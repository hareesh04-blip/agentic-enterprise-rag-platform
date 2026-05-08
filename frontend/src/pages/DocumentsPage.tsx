import { useEffect, useMemo, useState } from "react";
import type { ChangeEvent, FormEvent } from "react";
import { AxiosError } from "axios";
import { useNavigate } from "react-router-dom";
import { ingestionApi } from "../api/ingestionApi";
import { useAuth } from "../auth/AuthContext";
import type { DocumentItem, DocumentType, UploadDocumentResponse } from "../types/document";
import { accessLevelLabel, domainLabel } from "../utils/workspace";

const PROJECT_ID = 1;

function normalizeDocumentName(document: DocumentItem): string {
  return document.file_name || document.name || "Untitled document";
}

function badgeColorForDocType(type: string | null | undefined): string {
  if (type === "api") return "border-blue-200 bg-blue-50 text-blue-700";
  if (type === "product") return "border-emerald-200 bg-emerald-50 text-emerald-700";
  if (type === "hr") return "border-violet-200 bg-violet-50 text-violet-700";
  return "border-slate-200 bg-slate-50 text-slate-700";
}

function badgeColorForStatus(value: string | null | undefined): string {
  if (!value) return "border-slate-200 bg-slate-50 text-slate-700";
  if (value.includes("ok") || value.includes("stored") || value.includes("success")) {
    return "border-green-200 bg-green-50 text-green-700";
  }
  if (value.includes("failed") || value.includes("error")) {
    return "border-red-200 bg-red-50 text-red-700";
  }
  return "border-amber-200 bg-amber-50 text-amber-700";
}

export function DocumentsPage() {
  const { selectedKb, logout } = useAuth();
  const navigate = useNavigate();

  const [documents, setDocuments] = useState<DocumentItem[]>([]);
  const [listLoading, setListLoading] = useState(false);
  const [listError, setListError] = useState<string | null>(null);

  const [documentTypeFilter, setDocumentTypeFilter] = useState<"all" | DocumentType>("all");
  const [productNameFilter, setProductNameFilter] = useState("");

  const [file, setFile] = useState<File | null>(null);
  const [uploadDocumentType, setUploadDocumentType] = useState<DocumentType>("api");
  const [sourceDomain, setSourceDomain] = useState("");
  const [productName, setProductName] = useState("");
  const [version, setVersion] = useState("");
  const [uploadLoading, setUploadLoading] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [uploadSuccess, setUploadSuccess] = useState<string | null>(null);
  const [uploadResult, setUploadResult] = useState<UploadDocumentResponse | null>(null);

  const canViewDocuments = Boolean(selectedKb?.can_view_documents);
  const canUpload = Boolean(selectedKb?.can_upload);

  const fetchDocuments = async () => {
    if (!selectedKb || !canViewDocuments) return;
    setListLoading(true);
    setListError(null);
    try {
      const response = await ingestionApi.listDocuments({
        knowledge_base_id: selectedKb.id,
        document_type: documentTypeFilter === "all" ? undefined : documentTypeFilter,
        product_name: productNameFilter.trim() || undefined,
      });
      setDocuments(response.documents || []);
    } catch (err) {
      if (err instanceof AxiosError) {
        if (err.response?.status === 401) {
          logout();
          navigate("/login", { replace: true });
          return;
        }
        if (err.response?.status === 403) {
          setListError("You are not authorized to view documents for this knowledge base.");
          return;
        }
        setListError(typeof err.response?.data?.detail === "string" ? err.response.data.detail : "Failed to load documents.");
        return;
      }
      setListError("Failed to load documents.");
    } finally {
      setListLoading(false);
    }
  };

  useEffect(() => {
    void fetchDocuments();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedKb?.id, selectedKb?.can_view_documents, documentTypeFilter]);

  const onApplyFilters = async (event: FormEvent) => {
    event.preventDefault();
    await fetchDocuments();
  };

  const onFileChange = (event: ChangeEvent<HTMLInputElement>) => {
    setFile(event.target.files?.[0] ?? null);
  };

  const onUpload = async (event: FormEvent) => {
    event.preventDefault();
    if (!selectedKb || !canUpload) return;

    setUploadError(null);
    setUploadSuccess(null);
    setUploadResult(null);

    if (!file) {
      setUploadError("Please select a .docx file.");
      return;
    }

    const formData = new FormData();
    formData.append("project_id", String(PROJECT_ID));
    formData.append("knowledge_base_id", String(selectedKb.id));
    formData.append("document_type", uploadDocumentType);
    if (sourceDomain.trim()) formData.append("source_domain", sourceDomain.trim());
    if (productName.trim()) formData.append("product_name", productName.trim());
    if (version.trim()) formData.append("version", version.trim());
    formData.append("file", file);

    setUploadLoading(true);
    try {
      const response = await ingestionApi.uploadDocument(formData);
      setUploadResult(response);
      setUploadSuccess(`Uploaded successfully. Document ID: ${response.document_id ?? "N/A"}`);
      setFile(null);
      setSourceDomain("");
      setProductName("");
      setVersion("");
      await fetchDocuments();
    } catch (err) {
      if (err instanceof AxiosError) {
        if (err.response?.status === 401) {
          logout();
          navigate("/login", { replace: true });
          return;
        }
        setUploadError(typeof err.response?.data?.detail === "string" ? err.response.data.detail : "Upload failed.");
        return;
      }
      setUploadError("Upload failed.");
    } finally {
      setUploadLoading(false);
    }
  };

  const tableRows = useMemo(
    () =>
      documents.map((doc) => (
        <tr key={doc.id} className="border-t border-slate-200 text-sm text-slate-700">
          <td className="px-3 py-2 font-medium text-slate-900">{normalizeDocumentName(doc)}</td>
          <td className="px-3 py-2">
            <span className={`rounded-full border px-2 py-0.5 text-xs font-medium ${badgeColorForDocType(doc.document_type)}`}>
              {doc.document_type || "unknown"}
            </span>
          </td>
          <td className="px-3 py-2">{doc.product_name || "-"}</td>
          <td className="px-3 py-2">{doc.source_domain || "-"}</td>
          <td className="px-3 py-2">{doc.document_version || "-"}</td>
          <td className="px-3 py-2">{doc.chunk_count ?? "-"}</td>
          <td className="px-3 py-2">
            <span className={`rounded-full border px-2 py-0.5 text-xs font-medium ${badgeColorForStatus(doc.embedding_status)}`}>
              {doc.embedding_status || "-"}
            </span>
          </td>
          <td className="px-3 py-2">
            <span className={`rounded-full border px-2 py-0.5 text-xs font-medium ${badgeColorForStatus(doc.vector_store_status)}`}>
              {doc.vector_store_status || "-"}
            </span>
          </td>
          <td className="px-3 py-2">{doc.created_at ? new Date(doc.created_at).toLocaleString() : "-"}</td>
        </tr>
      )),
    [documents],
  );

  if (!selectedKb) {
    return (
      <div className="rounded-md border border-amber-200 bg-amber-50 p-4 text-sm text-amber-800">
        Select a Knowledge Base to view documents and upload new files. Document visibility remains KB-isolated.
      </div>
    );
  }

  if (!canViewDocuments) {
    return (
      <div className="rounded-md border border-red-200 bg-red-50 p-4 text-sm text-red-700">
        You are not authorized to view documents in the selected Knowledge Base.
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <section className="rounded-lg border border-slate-200 bg-slate-50 p-4">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <h2 className="text-lg font-semibold text-slate-900">Document Explorer</h2>
            <p className="mt-1 text-sm text-slate-600">
              KB scope: <span className="font-semibold text-slate-900">{selectedKb.name}</span> (ID: {selectedKb.id})
            </p>
            <div className="mt-2 flex flex-wrap gap-2 text-xs">
              <span className="rounded-full border border-blue-200 bg-blue-50 px-2 py-0.5 text-blue-700">
                Domain: {domainLabel(selectedKb.domain_type)}
              </span>
              <span className="rounded-full border border-emerald-200 bg-emerald-50 px-2 py-0.5 text-emerald-700">
                Access: {accessLevelLabel(selectedKb.access_level)}
              </span>
            </div>
          </div>
          <button
            type="button"
            onClick={() => void fetchDocuments()}
            disabled={listLoading}
            className="rounded-md border border-slate-300 bg-white px-3 py-1.5 text-sm font-medium text-slate-700 hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-50"
          >
            {listLoading ? "Refreshing..." : "Refresh"}
          </button>
        </div>

        <form onSubmit={onApplyFilters} className="mt-4 grid grid-cols-1 gap-3 md:grid-cols-4">
          <label className="space-y-1">
            <span className="text-xs font-semibold uppercase tracking-wide text-slate-500">Document type</span>
            <select
              value={documentTypeFilter}
              onChange={(event) => setDocumentTypeFilter(event.target.value as "all" | DocumentType)}
              className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
            >
              <option value="all">all</option>
              <option value="api">api</option>
              <option value="product">product</option>
              <option value="hr">hr</option>
            </select>
          </label>
          <label className="space-y-1 md:col-span-2">
            <span className="text-xs font-semibold uppercase tracking-wide text-slate-500">Product name</span>
            <input
              value={productNameFilter}
              onChange={(event) => setProductNameFilter(event.target.value)}
              placeholder="Exact product name filter"
              className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
            />
          </label>
          <div className="flex items-end">
            <button
              type="submit"
              disabled={listLoading}
              className="w-full rounded-md bg-slate-900 px-3 py-2 text-sm font-semibold text-white hover:bg-slate-800 disabled:cursor-not-allowed disabled:opacity-50"
            >
              Apply filters
            </button>
          </div>
        </form>
      </section>

      <section className="rounded-lg border border-slate-200 bg-white p-0">
        {listError ? <p className="border-b border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">{listError}</p> : null}
        {listLoading ? <p className="px-4 py-6 text-sm text-slate-600">Loading documents...</p> : null}
        {!listLoading && !listError && documents.length === 0 ? (
          <div className="px-4 py-6">
            <p className="text-sm font-medium text-slate-800">No documents found</p>
            <p className="mt-1 text-sm text-slate-600">Try changing filters or upload a document if your access level allows it.</p>
          </div>
        ) : null}
        {!listLoading && !listError && documents.length > 0 ? (
          <div className="overflow-x-auto">
            <table className="min-w-full">
              <thead className="bg-slate-50 text-left text-xs uppercase tracking-wide text-slate-500">
                <tr>
                  <th className="px-3 py-2">File</th>
                  <th className="px-3 py-2">Type</th>
                  <th className="px-3 py-2">Product</th>
                  <th className="px-3 py-2">Domain</th>
                  <th className="px-3 py-2">Version</th>
                  <th className="px-3 py-2">Chunks</th>
                  <th className="px-3 py-2">Embedding</th>
                  <th className="px-3 py-2">Vector</th>
                  <th className="px-3 py-2">Created</th>
                </tr>
              </thead>
              <tbody>{tableRows}</tbody>
            </table>
          </div>
        ) : null}
      </section>

      {canUpload ? (
        <section className="rounded-lg border border-slate-200 bg-white p-4">
          <h3 className="text-base font-semibold text-slate-900">Upload Document</h3>
          <p className="mt-1 text-sm text-slate-600">Knowledge base is fixed to the current selection. KB ID is not user-editable.</p>

          <form onSubmit={onUpload} className="mt-4 grid grid-cols-1 gap-3 md:grid-cols-2">
            <label className="space-y-1 md:col-span-2">
              <span className="text-xs font-semibold uppercase tracking-wide text-slate-500">File (.docx required)</span>
              <input type="file" accept=".docx" onChange={onFileChange} className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm" />
            </label>

            <label className="space-y-1">
              <span className="text-xs font-semibold uppercase tracking-wide text-slate-500">Document type *</span>
              <select
                value={uploadDocumentType}
                onChange={(event) => setUploadDocumentType(event.target.value as DocumentType)}
                className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
              >
                <option value="api">api</option>
                <option value="product">product</option>
                <option value="hr">hr</option>
              </select>
            </label>

            <label className="space-y-1">
              <span className="text-xs font-semibold uppercase tracking-wide text-slate-500">Source domain</span>
              <input
                value={sourceDomain}
                onChange={(event) => setSourceDomain(event.target.value)}
                placeholder="example.internal"
                className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
              />
            </label>

            <label className="space-y-1">
              <span className="text-xs font-semibold uppercase tracking-wide text-slate-500">Product name</span>
              <input
                value={productName}
                onChange={(event) => setProductName(event.target.value)}
                placeholder={uploadDocumentType === "product" ? "Recommended for product docs" : "Optional"}
                className={`w-full rounded-md border px-3 py-2 text-sm ${
                  uploadDocumentType === "product" ? "border-amber-300 bg-amber-50" : "border-slate-300"
                }`}
              />
            </label>

            <label className="space-y-1">
              <span className="text-xs font-semibold uppercase tracking-wide text-slate-500">Version</span>
              <input
                value={version}
                onChange={(event) => setVersion(event.target.value)}
                placeholder="v1.0"
                className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
              />
            </label>

            <div className="md:col-span-2">
              <button
                type="submit"
                disabled={uploadLoading}
                className="rounded-md bg-blue-600 px-4 py-2 text-sm font-semibold text-white hover:bg-blue-500 disabled:cursor-not-allowed disabled:opacity-50"
              >
                {uploadLoading ? "Uploading..." : "Upload and ingest"}
              </button>
            </div>
          </form>

          {uploadLoading ? (
            <p className="mt-3 rounded-md border border-blue-200 bg-blue-50 px-3 py-2 text-sm text-blue-700">
              Upload and ingestion in progress...
            </p>
          ) : null}
          {uploadError ? <p className="mt-3 rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">{uploadError}</p> : null}
          {uploadSuccess ? <p className="mt-3 rounded-md border border-green-200 bg-green-50 px-3 py-2 text-sm text-green-700">{uploadSuccess}</p> : null}

          {uploadResult ? (
            <div className="mt-3 rounded-md border border-slate-200 bg-slate-50 p-3 text-xs text-slate-700">
              <p className="mb-2 font-semibold text-slate-800">Upload Result</p>
              <div className="grid grid-cols-1 gap-2 md:grid-cols-2">
                <p>chunk_count: {uploadResult.chunk_count ?? "N/A"}</p>
                <p>vector_collection_name: {uploadResult.vector_collection_name ?? "N/A"}</p>
                <p>vector_embedding_dimension: {uploadResult.vector_embedding_dimension ?? "N/A"}</p>
                <p>embedding_status: {uploadResult.embedding_status ?? "N/A"}</p>
                <p>vector_store_status: {uploadResult.vector_store_status ?? "N/A"}</p>
                <p>qdrant_points_created: {uploadResult.qdrant_points_created ?? "N/A"}</p>
                <p>vector_sample_verified: {String(uploadResult.vector_sample_verified ?? "N/A")}</p>
              </div>
            </div>
          ) : null}
        </section>
      ) : (
        <section className="rounded-md border border-amber-200 bg-amber-50 p-4 text-sm text-amber-800">
          Upload is disabled for this Knowledge Base. Your current permission is read-only.
        </section>
      )}
    </div>
  );
}
