# Phase Breakdown

## Task 1: Implement Backend Unit Tests for Parser Service

Implement all test methods in `test_parser.py` following TODO patterns. Test precedence resolution, inputs.conf parsing (monitor, tcp, udp, splunktcp, http, script), outputs.conf parsing (tcpout groups, SSL, indexer discovery), props.conf/transforms.conf parsing, and sensitive value redaction using golden config fixtures.

Relevant Files:
- `/Users/johan/src/Splunk-autodoc/api/tests/unit/test_parser.py`
- `/Users/johan/src/Splunk-autodoc/api/tests/fixtures/splunk_configs.py`
- `/Users/johan/src/Splunk-autodoc/api/app/services/parser.py`
- `/Users/johan/src/Splunk-autodoc/api/tests/conftest.py`


## Task 2: Implement Backend Unit Tests for Resolver Service

Implement all test methods in `test_resolver.py` following TODO patterns. Test host building, protocol determination (splunktcp, http, syslog), output target resolution, transforms evaluation, edge building/merging, placeholder host creation, graph metadata generation, and canonical graph building using parsed config fixtures.

Relevant Files:
- `/Users/johan/src/Splunk-autodoc/api/tests/unit/test_resolver.py`
- `/Users/johan/src/Splunk-autodoc/api/app/services/resolver.py`
- `/Users/johan/src/Splunk-autodoc/api/tests/fixtures/splunk_configs.py`
- `/Users/johan/src/Splunk-autodoc/api/tests/conftest.py`


## Task 3: Implement Backend Unit Tests for Validator Service

Implement all test methods in `test_validator.py` following TODO patterns. Test detection of dangling outputs, unknown indexes, unsecured pipes (no TLS), drop paths (nullQueue), ambiguous groups, missing configs, circular routing, and complete validation workflows using canonical graph structures.

Relevant Files:
- `/Users/johan/src/Splunk-autodoc/api/tests/unit/test_validator.py`
- `/Users/johan/src/Splunk-autodoc/api/app/services/validator.py`
- `/Users/johan/src/Splunk-autodoc/api/tests/conftest.py`


## Task 4: Implement Backend Unit Tests for Storage Service

Implement all test methods in `test_storage.py` following TODO patterns. Test archive extraction (zip, tar.gz), file validation (magic bytes, size limits), safe path extraction (prevent path traversal), upload saving with streaming, parsed config storage, canonical graph storage, artifact cleanup, and listing extracted files.

Relevant Files:
- `/Users/johan/src/Splunk-autodoc/api/tests/unit/test_storage.py`
- `/Users/johan/src/Splunk-autodoc/api/app/services/storage.py`
- `/Users/johan/src/Splunk-autodoc/api/tests/conftest.py`


## Task 5: Implement Backend Unit Tests for Export Service

Implement all test methods in `test_export.py` following TODO patterns. Test DOT generation (node/edge styling, TLS, placeholders), JSON generation (pretty/minified), PNG/PDF/SVG generation (with `@pytest.mark.requires_graphviz`), graph filtering (by role, index, host), and export archive creation using canonical graph structures.

Relevant Files:
- `/Users/johan/src/Splunk-autodoc/api/tests/unit/test_export.py`
- `/Users/johan/src/Splunk-autodoc/api/app/services/export.py`
- `/Users/johan/src/Splunk-autodoc/api/tests/conftest.py`


## Task 6: Implement Backend Integration Tests for Uploads API

Create `test_api_uploads.py` following the pattern from `test_api_projects.py`. Test `POST /projects/{id}/uploads` (multipart/form-data, validation, storage), `GET /uploads/{id}`, `GET /projects/{id}/uploads` (list), and `DELETE /uploads/{id}` (cascade, file cleanup) using `client` fixture and `create_test_archive` helper.

Relevant Files:
- `/Users/johan/src/Splunk-autodoc/api/tests/integration/test_api_projects.py`
- `/Users/johan/src/Splunk-autodoc/api/app/routers/uploads.py`
- `/Users/johan/src/Splunk-autodoc/api/tests/conftest.py`
- `/Users/johan/src/Splunk-autodoc/api/tests/fixtures/splunk_configs.py`


## Task 7: Implement Backend Integration Tests for Jobs API

Create `test_api_jobs.py` following the pattern from `test_api_projects.py`. Test `POST /uploads/{id}/jobs`, `GET /jobs/{id}` (status, logs, timestamps), `GET /uploads/{id}/jobs` (list with filtering), job status transitions (pending → running → completed/failed), and preventing deletion of running jobs. Mock `process_job_sync` for faster tests.

Relevant Files:
- `/Users/johan/src/Splunk-autodoc/api/tests/integration/test_api_projects.py`
- `/Users/johan/src/Splunk-autodoc/api/app/routers/jobs.py`
- `/Users/johan/src/Splunk-autodoc/api/app/services/processor.py`
- `/Users/johan/src/Splunk-autodoc/api/tests/conftest.py`


## Task 8: Implement Backend Integration Tests for Graphs API

Create `test_api_graphs.py` following the pattern from `test_api_projects.py`. Test `GET /projects/{id}/graphs`, `GET /graphs/{id}`, `GET /graphs/{id}/findings`, `GET /graphs/{id}/query` (server-side filtering), `POST /graphs/{id}/validate`, and `GET /graphs/{id}/exports` (DOT/JSON/PNG/PDF formats) using `sample_graph` and `sample_finding` fixtures.

Relevant Files:
- `/Users/johan/src/Splunk-autodoc/api/tests/integration/test_api_projects.py`
- `/Users/johan/src/Splunk-autodoc/api/app/routers/graphs.py`
- `/Users/johan/src/Splunk-autodoc/api/tests/conftest.py`


## Task 9: Implement Backend End-to-End Integration Test

Create `test_end_to_end.py` with complete workflow tests: create project → upload archive → create job → wait for completion → verify graph → verify findings → test exports. Test parsing workflow (parse → resolve → validate pipeline), export workflow (all formats), and error handling (malformed configs, missing files) using real golden configs.

Relevant Files:
- `/Users/johan/src/Splunk-autodoc/api/tests/integration/test_api_projects.py`
- `/Users/johan/src/Splunk-autodoc/api/app/services/processor.py`
- `/Users/johan/src/Splunk-autodoc/api/tests/conftest.py`
- `/Users/johan/src/Splunk-autodoc/api/tests/fixtures/splunk_configs.py`


## Task 10: Implement Frontend Unit Tests for Custom Hooks

Implement tests for `useProjects`, `useUpload`, `useJobPolling`, and `useGraph` hooks in `hooks/__tests__/`. Use `renderHook` from `@testing-library/react`, `waitFor` for async operations, and MSW handlers. Test fetching on mount, CRUD operations, polling logic, status updates, error handling, and loading states.

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

Implement tests for `FilterPanel`, `NodeInspector`, and `EdgeInspector` components in `components/__tests__/`. Use `render`, `screen`, `fireEvent` from `@testing-library/react` and custom render wrapper. Test role/index/host filtering, clear filters, node/edge data display, interaction handlers, and UI state changes with MSW handlers.

Relevant Files:
- `/Users/johan/src/Splunk-autodoc/frontend/src/components/__tests__/FilterPanel.test.tsx`
- `/Users/johan/src/Splunk-autodoc/frontend/src/components/FilterPanel.tsx`
- `/Users/johan/src/Splunk-autodoc/frontend/src/components/NodeInspector.tsx`
- `/Users/johan/src/Splunk-autodoc/frontend/src/components/EdgeInspector.tsx`
- `/Users/johan/src/Splunk-autodoc/frontend/src/test/utils.tsx`
- `/Users/johan/src/Splunk-autodoc/frontend/src/test/mocks/handlers.ts`


## Task 12: Implement Frontend Unit Tests for Pages

Implement tests for `Projects`, `Upload`, `GraphExplorer`, and `Findings` pages in `pages/__tests__/`. Use `render`, `screen`, `fireEvent`, `waitFor` and custom render wrapper. Test project list rendering, create/delete dialogs, file drag-and-drop, upload progress, job status display, graph rendering, filter application, findings table, and navigation with MSW handlers.

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

Implement complete user workflow tests in `upload-flow.spec.ts` using Playwright. Test: create project → upload .zip → wait for job completion → view graph → apply filters → export graph (DOT/JSON) → view findings. Also test upload validation (invalid file), job failure display, and graph filtering using Playwright APIs against local dev server (http://localhost:5173).

Relevant Files:
- `/Users/johan/src/Splunk-autodoc/frontend/e2e/upload-flow.spec.ts`
- `/Users/johan/src/Splunk-autodoc/frontend/playwright.config.ts`
- `/Users/johan/src/Splunk-autodoc/frontend/src/pages/Projects.tsx`
- `/Users/johan/src/Splunk-autodoc/frontend/src/pages/Upload.tsx`
- `/Users/johan/src/Splunk-autodoc/frontend/src/pages/GraphExplorer.tsx`