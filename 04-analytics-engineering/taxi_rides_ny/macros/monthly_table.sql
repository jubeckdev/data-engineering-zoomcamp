{% materialization monthly_table, adapter='duckdb' %}
  {# Deduplication keys include pickup_datetime and service_type, so these
     independent batches cannot split a duplicate group. Stage all batches
     before atomically replacing the published relation. #}
  {% set marker = '/* monthly_batch */' %}
  {% if marker not in sql %}
    {{ exceptions.raise_compiler_error('monthly_table requires its batch marker') }}
  {% endif %}
  {% set destination = this.incorporate(type='table') %}
  {% set staging = make_intermediate_relation(destination) %}
  {% set stale = load_relation(staging) %}
  {% if stale is not none %}{% do adapter.drop_relation(stale) %}{% endif %}
  {{ run_hooks(pre_hooks, inside_transaction=False) }}
  {{ run_hooks(pre_hooks, inside_transaction=True) }}
  {% call statement('main', auto_begin=True) %}
    CREATE TABLE {{ staging }} AS
    {{ sql | replace(marker, 'AND FALSE') }}
  {% endcall %}
  {% do adapter.commit() %}
  {% set batches = run_query("SELECT DISTINCT service_type, date_trunc('month', pickup_datetime)::date AS month_start FROM " ~ ref('int_trips_unioned') ~ " ORDER BY 1,2") %}
  {% for batch in batches.rows %}
    {% if batch[1] is none %}
      {{ exceptions.raise_compiler_error('Null pickup month must be resolved before batching') }}
    {% endif %}
    {% set service = batch[0] | replace("'", "''") %}
    {% set month = batch[1] | string %}
    {% set predicate = "AND u.service_type='" ~ service ~ "' AND u.pickup_datetime >= DATE '" ~ month ~ "' AND u.pickup_datetime < DATE '" ~ month ~ "' + INTERVAL '1 month'" %}
    {{ log('Building ' ~ service ~ ' ' ~ month, info=True) }}
    {% call statement('batch_' ~ loop.index, auto_begin=True) %}
      INSERT INTO {{ staging }} {{ sql | replace(marker, predicate) }}
    {% endcall %}
    {% do adapter.commit() %}
  {% endfor %}
  {% call statement('begin_publish', auto_begin=True) %}SELECT 1{% endcall %}
  {% set existing = load_relation(destination) %}
  {% if existing is not none %}{% do adapter.drop_relation(existing) %}{% endif %}
  {% do adapter.rename_relation(staging, destination) %}
  {{ run_hooks(post_hooks, inside_transaction=True) }}
  {% do adapter.commit() %}
  {{ run_hooks(post_hooks, inside_transaction=False) }}
  {{ return({'relations': [destination]}) }}
{% endmaterialization %}
