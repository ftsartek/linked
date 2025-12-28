import createClient, { type Middleware } from 'openapi-fetch';
import type { paths } from './schema';
import { PUBLIC_API_BASE_URL } from '$env/static/public';

/**
 * Retrieves the CSRF token from cookies in the browser.
 * @returns The CSRF token value or null if not found
 */
function getCsrfToken(): string | null {
	if (typeof document === 'undefined') return null;

	const cookies = document.cookie.split(';');
	for (const cookie of cookies) {
		const [name, value] = cookie.trim().split('=');
		if (name === 'csrftoken' && value) {
			return decodeURIComponent(value);
		}
	}
	return null;
}

/**
 * Middleware that adds CSRF token to state-changing requests.
 * Reads the token from the 'csrftoken' cookie and adds it as the 'x-csrftoken' header.
 */
const csrfMiddleware: Middleware = {
	async onRequest({ request }) {
		const method = request.method.toUpperCase();
		const isStateChanging = ['POST', 'PUT', 'DELETE', 'PATCH'].includes(method);

		if (isStateChanging) {
			const csrfToken = getCsrfToken();
			if (csrfToken) {
				request.headers.set('x-csrftoken', csrfToken);
			}
		}

		return request;
	}
};

export const apiClient = createClient<paths>({
	baseUrl: PUBLIC_API_BASE_URL,
	fetch: (input: Request) => fetch(input, { credentials: 'include' })
});

// Apply CSRF middleware to all API requests
apiClient.use(csrfMiddleware);

/**
 * Constructs a full URL by combining the API base URL with a relative path.
 * @param path - The relative path from the API (e.g., "/images/blog/image.jpg")
 * @returns The complete URL
 */
export function getApiUrl(path: string): string {
	if (!path) return '';
	// Handle paths that already include the protocol
	if (path.startsWith('http://') || path.startsWith('https://')) {
		return path;
	}
	// Ensure path starts with /
	const normalizedPath = path.startsWith('/') ? path : `/${path}`;
	return `${PUBLIC_API_BASE_URL}${normalizedPath}`;
}