terraform {
  required_version = ">= 1.9, < 2.0"
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 6.0"
    }
  }
}

provider "google" {
  project = var.project_id
  region  = var.region
}

variable "project_id" {
  description = "Existing GCP project with billing and required APIs enabled."
  type        = string
}

variable "region" {
  type    = string
  default = "europe-west3"
}

variable "location" {
  type    = string
  default = "EU"
}

resource "google_storage_bucket" "taxi" {
  name                        = "${var.project_id}-zoomcamp-taxi"
  location                    = var.location
  uniform_bucket_level_access = true
  public_access_prevention    = "enforced"
  force_destroy               = false
}

resource "google_bigquery_dataset" "taxi" {
  dataset_id                 = "zoomcamp_taxi"
  location                   = var.location
  delete_contents_on_destroy = false
}

output "bucket_name" {
  value = google_storage_bucket.taxi.name
}

output "dataset_id" {
  value = google_bigquery_dataset.taxi.dataset_id
}
