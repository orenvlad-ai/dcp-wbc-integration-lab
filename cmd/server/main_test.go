package main

import (
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"testing"
)

func testProvenance() provenance {
	return provenance{
		Repository:     repository,
		DeployedSHA:    "1111111111111111111111111111111111111111",
		ArtifactDigest: "2222222222222222222222222222222222222222222222222222222222222222",
		ManifestDigest: "3333333333333333333333333333333333333333333333333333333333333333",
		Environment:    environment,
		Service:        service,
	}
}

func TestHealthAndProvenance(t *testing.T) {
	h := handler(testProvenance())
	for _, path := range []string{"/healthz", "/provenance"} {
		req := httptest.NewRequest(http.MethodGet, path, nil)
		res := httptest.NewRecorder()
		h.ServeHTTP(res, req)
		if res.Code != http.StatusOK {
			t.Fatalf("%s status = %d", path, res.Code)
		}
		if got := res.Header().Get("Cache-Control"); got != "no-store" {
			t.Fatalf("%s Cache-Control = %q", path, got)
		}
	}

	health := httptest.NewRecorder()
	h.ServeHTTP(health, httptest.NewRequest(http.MethodGet, "/healthz", nil))
	var healthBody map[string]string
	if err := json.Unmarshal(health.Body.Bytes(), &healthBody); err != nil {
		t.Fatal(err)
	}
	if healthBody["status"] != "ok" || healthBody["service"] != service {
		t.Fatalf("health = %#v", healthBody)
	}

	res := httptest.NewRecorder()
	h.ServeHTTP(res, httptest.NewRequest(http.MethodGet, "/provenance", nil))
	var got provenance
	if err := json.Unmarshal(res.Body.Bytes(), &got); err != nil {
		t.Fatal(err)
	}
	if got != testProvenance() {
		t.Fatalf("provenance = %#v", got)
	}
}

func TestUnknownAndMutationRoutesFail(t *testing.T) {
	h := handler(testProvenance())
	res := httptest.NewRecorder()
	h.ServeHTTP(res, httptest.NewRequest(http.MethodPost, "/healthz", nil))
	if res.Code != http.StatusMethodNotAllowed {
		t.Fatalf("POST /healthz status = %d", res.Code)
	}
	res = httptest.NewRecorder()
	h.ServeHTTP(res, httptest.NewRequest(http.MethodGet, "/unknown", nil))
	if res.Code != http.StatusNotFound {
		t.Fatalf("GET /unknown status = %d", res.Code)
	}
}
