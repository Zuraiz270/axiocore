-- CreateEnum
CREATE TYPE "DocumentStatus" AS ENUM ('INGESTED', 'EXTRACTING', 'PENDING_REVIEW', 'IN_REVIEW', 'APPROVED', 'REJECTED', 'EXTRACTION_FAILED', 'STORED', 'DLQ');

-- CreateEnum
CREATE TYPE "PriorityQueue" AS ENUM ('high', 'low');

-- CreateEnum
CREATE TYPE "OutboxStatus" AS ENUM ('PENDING', 'PUBLISHED', 'FAILED');

-- CreateTable
CREATE TABLE "documents" (
    "id" UUID NOT NULL,
    "tenant_id" UUID NOT NULL,
    "original_filename" TEXT NOT NULL,
    "mime_type" TEXT NOT NULL,
    "file_size_bytes" INTEGER NOT NULL,
    "page_count" INTEGER NOT NULL,
    "storage_path" TEXT NOT NULL,
    "status" "DocumentStatus" NOT NULL DEFAULT 'INGESTED',
    "priority_queue" "PriorityQueue" NOT NULL,
    "requires_consensus" BOOLEAN NOT NULL DEFAULT false,
    "confidence_score" DOUBLE PRECISION,
    "reviewer_id" UUID,
    "locked_at" TIMESTAMP(3),
    "extraction_version" INTEGER NOT NULL DEFAULT 1,
    "schema_type" TEXT NOT NULL,
    "source_type" TEXT NOT NULL,
    "artifact_hash_set" TEXT,
    "created_at" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMP(3) NOT NULL,

    CONSTRAINT "documents_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "reviews" (
    "id" UUID NOT NULL,
    "document_id" UUID NOT NULL,
    "reviewer_id" UUID NOT NULL,
    "tenant_id" UUID NOT NULL,
    "status" TEXT NOT NULL,
    "comment" TEXT,
    "created_at" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "reviews_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "outbox_events" (
    "id" UUID NOT NULL,
    "tenant_id" UUID NOT NULL,
    "aggregate_type" TEXT NOT NULL,
    "aggregate_id" UUID NOT NULL,
    "event_type" TEXT NOT NULL,
    "payload" JSONB NOT NULL,
    "status" "OutboxStatus" NOT NULL DEFAULT 'PENDING',
    "created_at" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "published_at" TIMESTAMP(3),

    CONSTRAINT "outbox_events_pkey" PRIMARY KEY ("id")
);

-- CreateIndex
CREATE INDEX "documents_tenant_id_status_idx" ON "documents"("tenant_id", "status");

-- CreateIndex
CREATE INDEX "documents_tenant_id_locked_at_idx" ON "documents"("tenant_id", "locked_at");

-- CreateIndex
CREATE INDEX "reviews_document_id_idx" ON "reviews"("document_id");

-- CreateIndex
CREATE INDEX "reviews_tenant_id_idx" ON "reviews"("tenant_id");

-- CreateIndex
CREATE INDEX "outbox_events_status_created_at_idx" ON "outbox_events"("status", "created_at");

-- AddForeignKey
ALTER TABLE "reviews" ADD CONSTRAINT "reviews_document_id_fkey" FOREIGN KEY ("document_id") REFERENCES "documents"("id") ON DELETE RESTRICT ON UPDATE CASCADE;
