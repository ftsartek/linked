# Linked

Linked is a **work-in-progress** EVE Online Wormhole tracking tool. 

The primary goal is to bridge the gap between simpler and faster tracking tools like Tripwire and more feature-rich but slower tools like Pathfinder. This comes from a few design decisions:
  - Based on the highly performant [Litestar](https://litestar.dev/) and [SvelteKit](https://kit.svelte.dev/) projects.
  - Utilises SSE for incoming real-time updates while minimising inbound and outbound data requirements.
  - Underlaid with PostgreSQL & Valkey for data persistence and caching.
  
This project is still under heavy development and is fairly early in its lifecycle. Expect bugs! More features are on their way. Please create an issue for any bugs or feature requests.

# Development

Linked consists of two primary components:

- Web: the SvelteKit-based frontend application - requires NodeJS >= 22.12 & package management via NPM
- API: the Litestar-based backend application - requires Python >= 3.14 & package management via UV

It also has a couple dependencies:
  - Postgres (16+, 18 recommended)
  - Valkey (8+)
  
While developing, if you've got a reasonably recent Docker version available, you can spin up a localhost stack with Dockerised dependencies:
```
# If you haven't got the SDE/ESI data already collected, run:
make cli CMD="collect all" # If user_agent's not set in your env, use something like `--user-agent='LinkedEVE-<owner>/0.1.0 (youremail@example.com)'`
make dev
```
This'll spin up the API at `http://localhost:8000` and web at `http://localhost:5173`; Postgres & Redis will be running locally in Docker.

### Quality Control

Use [pre-commit](https://pre-commit.com/) to ensure your code is up to spec. Easiest way to install it is `uv tool install pre-commit` (or `pipx` if you prefer, but we assume you've got `uv` anyway). Simply install the hooks with `pre-commit install` and the code will be checked before each commit.

# Production

When hosting a production environment, both the frontend and backend should be behind a reverse proxy. NGINX is recommended, but you can use any solution that does the trick.

There are a few important considerations:
  - Setup is much easier when both services share a URI - the suggested approach is to have the proxy pass the base path to the web service and then route the subpath /api to the API service.
    - If you _do_ choose to separate these (e.g. `example.com` for the web service and `api.example.com` for the API) you will need to configure CORS & CSRF for the API (which can be done via .env or the relevant environment variables).
  - The reverse proxy needs to be configured such that the SSE URL - /maps/<map_id>/events - does not have a read timeout. While generally the client will automatically reconnect when dropped, it's not a great experience.

The recommended approach to hosting is a Docker Compose setup with 6 containers. This will likely be expanded with an actual example (and probably prebuilt images) in future, but this would look like:

- Linked API
- Linked Web
- [Postgres](https://hub.docker.com/_/postgres/)
- [Valkey](https://hub.docker.com/r/valkey/valkey)
- [NGINX Proxy](https://hub.docker.com/r/nginxproxy/nginx-proxy)
- [Acme Companion](https://hub.docker.com/r/nginxproxy/acme-companion)
