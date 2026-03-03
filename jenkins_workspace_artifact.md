# Jenkins Notes: Workspace vs Artifact

## 1. Workspace

### Definition

A workspace is the directory on the Jenkins agent where your job runs.
It contains the checked-out source code and all temporary build files.

### What Happens in a Workspace

-   Jenkins checks out your repository here.
-   Build commands run inside this directory.
-   Docker builds use files from this location.
-   Temporary files and logs are generated here.

### Typical Location (Linux)

    /var/lib/jenkins/workspace/<job-name>/

For multibranch pipelines:

    /var/lib/jenkins/workspace/<job-name>/<branch-name>/

### Key Characteristics

-   Temporary (may be cleaned between builds)
-   Used only during execution
-   Can be reused if not cleaned
-   Not meant for long-term storage

------------------------------------------------------------------------

## 2. Artifact

### Definition

An artifact is a file (or files) produced by the build that you want to
keep after the job finishes.

It is the final output of your pipeline.

### Examples of Artifacts

Backend: - .jar - .war - .whl - .tar.gz

Frontend: - dist/ folder

CI Reports: - junit XML reports - coverage reports - HTML test reports

Docker: - Exported image tar - Pushed Docker image (treated as
deployable artifact)

### Why Artifacts Matter

-   Allow downloads from Jenkins UI
-   Used for deployments
-   Passed between pipeline stages
-   Provide build traceability
-   Preserve build history

### Storage Location

Usually stored under:

    /var/lib/jenkins/jobs/<job-name>/builds/<build-number>/archive/

------------------------------------------------------------------------

## 3. Workspace vs Artifact (Comparison)

  Feature    Workspace                        Artifact
  ---------- -------------------------------- ------------------------------------
  Purpose    Working directory during build   Final output of build
  Lifetime   Temporary                        Stored (based on retention policy)
  Location   On Jenkins agent                 Archived in Jenkins
  Used For   Build & test execution           Deployment & download

------------------------------------------------------------------------

## 4. CI/CD Flow Example

Code Commit ↓ Workspace Created ↓ Build & Test Run ↓ Artifact Generated
↓ Artifact Archived ↓ Deployment Uses Artifact

------------------------------------------------------------------------

End of Notes
