# Linked

Linked is a Wormhole Mapping application for EVE Online. It allows shared map access with real-time updates, and integration with the EVE Online ESI API.

## API

The API component - under `api/` - handles:
- Updating source data via the ESI API and ESD static data source.
- Providing storage for wormhole map data, user data, etc
- An HTTP API, including an SSE endpoint for real-time updates, authenticated via EVE ESI character access tokens.

The API component relies on the following dependencies:
- Python 3.14
- Litestar (https://litestar.dev) - API
- SQLSpec (https://sqlspec.dev) - Database management (using AsyncPG as a DBAPI)
- Msgspec (https://github.com/jcrist/msgspec) - Structure & data de/serialization
- Valkey (libvalkey) - Caching & session storage

The API is primarily Asynchronous and we should strive to use async whenever we reasonably can.

## Web

The web component - under `web/` - handles:
- A user interface for the API

The web component relies on the following dependencies:
- Typescript
- Svelte 5 (https://svelte.dev/) - UI Framework with SvelteKit 2
- Skeleton UI 4 (https://www.skeleton.dev/) - Component & Style Framework
- Tailwind CSS 4 (https://tailwindcss.com/) - Style Framework
- SvelteFlow (https://svelteflow.dev/) - Map visualisation
- OpenAPI Typescript & OpenAPI Fetch (https://openapi-ts.dev/) - API Documentation & Client - types are generated using the `make schema` command.

## Useful Information

### Server Sent Events

Whenever one logged-in client sends successful map update events (which are persisted via individual API requests), 
any other user connected to the same map (this SSE connection is instantiated upon map selection) will receive the update via the SSE endpoint (`/maps/{map_id:uuid}/events`). This is also the exception to the use of the API client; this is direct as OpenAPI does not cleanly define SSE.

### Access Control

Authentication is managed per-user; multiple characters can be associated with a user account.
Access itself is more flexible, using a pattern of:
- Owner (user association)
- User shared (explicit sharing for a user associated with a specific character)
- Corporation shared (sharing for any user with a character associated with a permitted corporation)
- Alliance shared (sharing for any user with a character associated with a permitted alliance)

Owners always retain full access & control. Any shared access can be restricted to read only - whether access is RO or RW is entirely dependent on the finest grain of control - a user with read-only access will have read-only access, even if their corporation or alliance has read-write access.

### Map Settings

Most map settings - i.e. how a map looks - are persisted on a per-map basis in the database and can be controlled only by the owner.

### Map Data

Map data consists of Nodes (which relate to solar systems) and Connections (which relate to connections between solar systems).

### Styling

The Web UI is styled using Tailwind + Skeleton - currently only dark mode support. The primary theming patterns used are:
- `bg-surface-950/75 backdrop-blur-2xl` for page-level components (no borders)
- `bg-black/40 backdrop-blur-xs` for modal/dialog components and `bg-black/50 backdrop-blur-sm` for the modal/dialogs themselves (again, no borders)
- `bg-black border-2 border-secondary-950` for input components
- `hover:bg-primary-950/60` for hover states on dropdown selections, etc.
- `

## Code Quality

### Web

The `web/` section of the project is formatted with `npm run format`, checked with `npm run lint` and `npm run check`.

### API

The `api/` section of the project is formatted with `uv run ruff format`, checked with `uv run ruff check --fix`, and type checked with `uv run ty check`


## Database

Database migrations should be created and managed using SQLSpec's migration process, which puts the migration templates in api/migrations.
