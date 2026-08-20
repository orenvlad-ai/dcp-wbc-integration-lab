package main

import (
	"encoding/json"
	"errors"
	"flag"
	"fmt"
	"log"
	"net/http"
	"os"
	"regexp"
	"time"
)

const (
	repository  = "orenvlad-ai/dcp-wbc-integration-lab"
	environment = "dcp-wbc-integration-lab-selectel"
	service     = "dcp-wbc-integration-lab"
	defaultAddr = "127.0.0.1:18321"
)

var buildSHA = "unbuilt"

var (
	shaPattern    = regexp.MustCompile(`^[0-9a-f]{40}$`)
	digestPattern = regexp.MustCompile(`^[0-9a-f]{64}$`)
)

type provenance struct {
	Repository     string `json:"repository"`
	DeployedSHA    string `json:"deployed_sha"`
	ArtifactDigest string `json:"artifact_digest"`
	ManifestDigest string `json:"manifest_digest"`
	Environment    string `json:"environment"`
	Service        string `json:"service"`
}

func loadProvenance() (provenance, error) {
	p := provenance{
		Repository:     repository,
		DeployedSHA:    buildSHA,
		ArtifactDigest: os.Getenv("DCP_LAB_ARTIFACT_SHA256"),
		ManifestDigest: os.Getenv("DCP_LAB_MANIFEST_SHA256"),
		Environment:    environment,
		Service:        service,
	}
	if !shaPattern.MatchString(p.DeployedSHA) {
		return provenance{}, errors.New("invalid deployed SHA")
	}
	if !digestPattern.MatchString(p.ArtifactDigest) {
		return provenance{}, errors.New("invalid artifact digest")
	}
	if !digestPattern.MatchString(p.ManifestDigest) {
		return provenance{}, errors.New("invalid manifest digest")
	}
	return p, nil
}

func handler(p provenance) http.Handler {
	mux := http.NewServeMux()
	mux.HandleFunc("GET /healthz", func(w http.ResponseWriter, _ *http.Request) {
		w.Header().Set("Content-Type", "application/json")
		w.Header().Set("Cache-Control", "no-store")
		w.Header().Set("X-Content-Type-Options", "nosniff")
		_ = json.NewEncoder(w).Encode(map[string]string{"status": "ok"})
	})
	mux.HandleFunc("GET /provenance", func(w http.ResponseWriter, _ *http.Request) {
		w.Header().Set("Content-Type", "application/json")
		w.Header().Set("Cache-Control", "no-store")
		w.Header().Set("X-Content-Type-Options", "nosniff")
		_ = json.NewEncoder(w).Encode(p)
	})
	return mux
}

func main() {
	printBuildSHA := flag.Bool("build-sha", false, "print immutable build SHA")
	flag.Parse()
	if *printBuildSHA {
		fmt.Println(buildSHA)
		return
	}

	p, err := loadProvenance()
	if err != nil {
		log.Fatal(err)
	}
	addr := os.Getenv("DCP_LAB_LISTEN_ADDR")
	if addr == "" {
		addr = defaultAddr
	}
	if addr != defaultAddr {
		log.Fatal("listener identity drift")
	}

	server := &http.Server{
		Addr:              addr,
		Handler:           handler(p),
		ReadHeaderTimeout: 5 * time.Second,
		ReadTimeout:       5 * time.Second,
		WriteTimeout:      5 * time.Second,
		IdleTimeout:       30 * time.Second,
		MaxHeaderBytes:    8 << 10,
	}
	log.Printf("starting %s at %s for %s", service, addr, buildSHA)
	log.Fatal(server.ListenAndServe())
}
