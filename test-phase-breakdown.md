# Phase Breakdown

## Task 1: Implement Backend Unit Tests for Parser Service

Implement all test methods in `/api/tests/unit/test_parser.py` following the established TODO patterns. Use golden config fixtures from `tests/fixtures/splunk_configs.py` (e.g., `create_uf_config`, `create_hf_config`). Test precedence resolution, inputs.conf parsing (monitor, tcp, udp, splunktcp, http, script), outputs.conf parsing (tcpout groups, SSL, indexer discovery), props.conf parsing (sourcetype/source/host stanzas, transforms references), transforms.conf parsing (index routing, drops, sourcetype rewrites), and sensitive value redaction.

Relevant Files:
- `/Users/johan/src/Splunk-autodoc/api/tests/unit/test_parser.py`
- `/Users/johan/src/Splunk-autodoc/api/tests/fixtures/splunk_configs.py`
- `/Users/johan/src/Splunk-autodoc/api/app/services/parser.py`
- `/Users/johan/src/Splunk-autodoc/api/tests/conftest.py`


## Task 2: Implement Backend Unit Tests for Resolver Service

Implement all test methods in `/api/tests/unit/test_resolver.py` following the established TODO patterns. Test host building from parsed configs, protocol determination (splunktcp, http, syslog), output target resolution, transforms evaluation order, edge building and merging, placeholder host creation for unknown destinations, graph metadata generation, and complete canonical graph building. Use parsed config fixtures from parser tests.

Relevant Files:
- `/Users/johan/src/Splunk-autodoc/api/tests/unit/test_resolver.py`
- `/Users/johan/src/Splunk-autodoc/api/app/services/resolver.py`
- `/Users/johan/src/Splunk-autodoc/api/tests/fixtures/splunk_configs.py`
- `/Users/johan/src/Splunk-autodoc/api/tests/conftest.py`


## Task 3: Implement Backend Unit Tests for Validator Service

Implement all test methods in `/api/tests/unit/test_validator.py` following the established TODO patterns. Test detection of dangling outputs, unknown indexes, unsecured pipes (no TLS), drop paths (nullQueue), ambiguous groups (no defaultGroup), missing configs, circular routing, and complete validation workflows. Use canonical graph structures from resolver tests.

Relevant Files:
- `/Users/johan/src/Splunk-autodoc/api/tests/unit/test_validator.py`
- `/Users/johan/src/Splunk-autodoc/api/app/services/validator.py`
- `/Users/johan/src/Splunk-autodoc/api/tests/conftest.py`


## Task 4: Implement Backend Unit Tests for Storage Service

Implement all test methods in `/api/tests/unit/test_storage.py` following the established TODO patterns. Test archive extraction (zip, tar.gz), file validation (magic bytes, size limits), safe path extraction (prevent path traversal), upload saving with streaming, parsed config storage, canonical graph storage, artifact cleanup, and listing extracted files. Use `temp_storage_root` fixture and `create_test_archive` helper.

Relevant Files:
- `/Users/johan/src/Splunk-autodoc/api/tests/unit/test_storage.py`
- `/Users/johan/src/Splunk-autodoc/api/app/services/storage.py`
- `/Users/johan/src/Splunk-autodoc/api/tests/conftest.py`


## Task 5: Implement Backend Unit Tests for Export Service

Implement all test methods in `/api/tests/unit/test_export.py` following the established TODO patterns. Test DOT generation (node styling by role, edge labels, TLS styling, placeholder styling), JSON generation (pretty print, minified, serialization), PNG/PDF/SVG generation (requires Graphviz, use `@pytest.mark.requires_graphviz`), graph filtering (by role, index, host), and export archive creation. Use canonical graph structures.

Relevant Files:
- `/Users/johan/src/Splunk-autodoc/api/tests/unit/test_export.py`
- `/Users/johan/src/Splunk-autodoc/api/app/services/export.py`
- `/Users/johan/src/Splunk-autodoc/api/tests/conftest.py`


## Task 6: Implement Backend Integration Tests for Uploads API

Create `/api/tests/integration/test_api_uploads.py` following the pattern from `test_api_projects.py`. Test `POST /projects/{id}/uploads` (file upload with multipart/form-data, validation, storage), `GET /uploads/{id}`, `GET /projects/{id}/uploads` (list), and `DELETE /uploads/{id}` (with cascade and file cleanup). Use `client` fixture with DB override, `sample_project` fixture, and `create_test_archive` helper for realistic uploads.

Relevant Files:
- `/Users/johan/src/Splunk-autodoc/api/tests/integration/test_api_projects.py`
- `/Users/johan/src/Splunk-autodoc/api/app/routers/uploads.py`
- `/Users/johan/src/Splunk-autodoc/api/tests/conftest.py`
- `/Users/johan/src/Splunk-autodoc/api/tests/fixtures/splunk_configs.py`


## Task 7: Implement Backend Integration Tests for Jobs API

Create `/api/tests/integration/test_api_jobs.py` following the pattern from `test_api_projects.py`. Test `POST /uploads/{id}/jobs` (create job, trigger processing), `GET /jobs/{id}` (status, logs, timestamps), `GET /uploads/{id}/jobs` (list with status filtering), job status transitions (pending → running → completed/failed), and preventing deletion of running jobs. Use `client` fixture, `sample_upload` fixture, and mock `process_job_sync` for faster tests.

Relevant Files:
- `/Users/johan/src/Splunk-autodoc/api/tests/integration/test_api_projects.py`
- `/Users/johan/src/Splunk-autodoc/api/app/routers/jobs.py`
- `/Users/johan/src/Splunk-autodoc/api/app/services/processor.py`
- `/Users/johan/src/Splunk-autodoc/api/tests/conftest.py`


## Task 8: Implement Backend Integration Tests for Graphs API

Create `/api/tests/integration/test_api_graphs.py` following the pattern from `test_api_projects.py`. Test `GET /projects/{id}/graphs` (list with filtering), `GET /graphs/{id}` (retrieve canonical JSON), `GET /graphs/{id}/findings`, `GET /graphs/{id}/query` (server-side filtering by host/index/protocol), `POST /graphs/{id}/validate` (re-run validation), and `GET /graphs/{id}/exports` (DOT/JSON/PNG/PDF formats). Use `client` fixture, `sample_graph` fixture, and `sample_finding` fixture.

Relevant Files:
- `/Users/johan/src/Splunk-autodoc/api/tests/integration/test_api_projects.py`
- `/Users/johan/src/Splunk-autodoc/api/app/routers/graphs.py`
- `/Users/johan/src/Splunk-autodoc/api/tests/conftest.py`


## Task 9: Implement Backend End-to-End Integration Test

Create `/api/tests/integration/test_end_to_end.py` with complete workflow tests: create project → upload archive → create job → wait for completion → verify graph → verify findings → test exports. Test parsing workflow (parse → resolve → validate pipeline), export workflow (generate all formats), and error handling (malformed configs, missing files). Use all fixtures and test the complete `processor.py` pipeline with real golden configs.

Relevant Files:
- `/Users/johan/src/Splunk-autodoc/api/tests/integration/test_api_projects.py`
- `/Users/johan/src/Splunk-autodoc/api/app/services/processor.py`
- `/Users/johan/src/Splunk-autodoc/api/tests/conftest.py`
- `/Users/johan/src/Splunk-autodoc/api/tests/fixtures/splunk_configs.py`


## Task 10: Implement Frontend Unit Tests for Custom Hooks

Implement tests for `useProjects`, `useUpload`, `useJobPolling`, and `useGraph` hooks in `/frontend/src/hooks/__tests__/`. Use `renderHook` from `@testing-library/react`, `waitFor` for async operations, and MSW handlers from `/frontend/src/test/mocks/handlers.ts`. Test fetching data on mount, create/update/delete operations, polling logic, status updates, error handling, and loading states. Follow the pattern from existing component tests.

Relevant Files:
- `/Users/johan/src/Splunk-autodoc/frontend/src/hooks/__tests__/useProjects.test.ts`
- `/Users/johan/src/Splunk-autodoc/frontend/src/hooks/__tests__/useJobPolling.test.ts`
- `/Users/johan/src/Splunk-autodoc/frontend/src/hooks/useProjects.ts`
- `/Users/johan/src/Splunk-autodoc/frontend/src/hooks/useUpload.ts`
- `/Users/johan/src/Splunk-autodoc/frontend/src/hooks/useJobPolling.ts`
- `/Users/johan/src/Splunk-autodoc/frontend/src/hooks/useGraph.ts`
- `/Users/johan/src/Splunk-autodoc/frontend/src/test/mocks/handlers.ts`
- `/Users/johan/src/Splunk-autodoc/frontend/src/test/setup.ts`


## Task 11: Implement Frontend Unit Tests for Components

Implement tests for `FilterPanel`, `NodeInspector`, and `EdgeInspector` components in `/frontend/src/components/__tests__/`. Use `render`, `screen`, `fireEvent` from `@testing-library/react` and the custom `render` wrapper from `/frontend/src/test/utils.tsx`. Test role/index/host filtering, clear filters, node/edge data display, interaction handlers, and UI state changes. Mock API responses with MSW handlers.

Relevant Files:
- `/Users/johan/src/Splunk-autodoc/frontend/src/components/__tests__/FilterPanel.test.tsx`
- `/Users/johan/src/Splunk-autodoc/frontend/src/components/FilterPanel.tsx`
- `/Users/johan/src/Splunk-autodoc/frontend/src/components/NodeInspector.tsx`
- `/Users/johan/src/Splunk-autodoc/frontend/src/components/EdgeInspector.tsx`
- `/Users/johan/src/Splunk-autodoc/frontend/src/test/utils.tsx`
- `/Users/johan/src/Splunk-autodoc/frontend/src/test/mocks/handlers.ts`


## Task 12: Implement Frontend Unit Tests for Pages

Implement tests for `Projects`, `Upload`, `GraphExplorer`, and `Findings` pages in `/frontend/src/pages/__tests__/`. Use `render`, `screen`, `fireEvent`, `waitFor` from `@testing-library/react` and the custom render wrapper. Test project list rendering, create/delete dialogs, file drag-and-drop, upload progress, job status display, graph rendering, filter application, findings table, and navigation. Mock API responses with MSW handlers.

Relevant Files:
- `/Users/johan/src/Splunk-autodoc/frontend/src/pages/__tests__/Projects.test.tsx`
- `/Users/johan/src/Splunk-autodoc/frontend/src/pages/__tests__/Upload.test.tsx`
- `/Users/johan/src/Splunk-autodoc/frontend/src/pages/Projects.tsx`
- `/Users/johan/src/Splunk-autodoc/frontend/src/pages/Upload.tsx`
- `/Users/johan/src/Splunk-autodoc/frontend/src/pages/GraphExplorer.tsx`
- `/Users/johan/src/Splunk-autodoc/frontend/src/pages/Findings.tsx`
- `/Users/johan/src/Splunk-autodoc/frontend/src/test/utils.tsx`
- `/Users/johan/src/Splunk-autodoc/frontend/src/test/mocks/handlers.ts`


## Task 13: Implement Frontend E2E Tests with Playwright

Implement complete user workflow tests in `/frontend/e2e/upload-flow.spec.ts` using Playwright. Test: create project → upload .zip file → wait for job completion → view graph in explorer → apply filters → export graph (DOT/JSON) → view findings. Also test upload validation (invalid file), job failure display, and graph filtering. Use `page.goto`, `page.click`, `page.fill`, `page.setInputFiles`, `expect().toBeVisible()`, and `page.waitForEvent('download')`. Configure to run against local dev server (http://localhost:5173).

Relevant Files:
- `/Users/johan/src/Splunk-autodoc/frontend/e2e/upload-flow.spec.ts`
- `/Users/johan/src/Splunk-autodoc/frontend/playwright.config.ts`
- `/Users/johan/src/Splunk-autodoc/frontend/src/pages/Projects.tsx`
- `/Users/johan/src/Splunk-autodoc/frontend/src/pages/Upload.tsx`
- `/Users/johan/src/Splunk-autodoc/frontend/src/pages/GraphExplorer.tsx`