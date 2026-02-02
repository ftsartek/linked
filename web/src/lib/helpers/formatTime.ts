/**
 * Format a date string as a short relative time (e.g., "5s", "3m", "2h").
 */
export function formatTimeAgo(dateStr: string | null): string {
	if (!dateStr) return '';
	const date = new Date(dateStr);
	const diffMs = Date.now() - date.getTime();
	const diffSecs = Math.floor(diffMs / 1000);
	if (diffSecs < 60) return `${diffSecs}s`;
	if (diffSecs < 3600) return `${Math.floor(diffSecs / 60)}m`;
	return `${Math.floor(diffSecs / 3600)}h`;
}

/**
 * Format a date string as a longer relative time (e.g., "5s ago", "3m 20s ago", "2h 15m ago").
 */
export function formatLastUpdated(dateStr: string, currentTime: number): string {
	const date = new Date(dateStr);
	const diffMs = currentTime - date.getTime();
	const diffSecs = Math.floor(diffMs / 1000);

	if (diffSecs < 60) return `${diffSecs}s ago`;
	if (diffSecs < 600) {
		const mins = Math.floor(diffSecs / 60);
		const secs = diffSecs % 60;
		return `${mins}m ${secs}s ago`;
	}
	if (diffSecs < 3600) return `${Math.floor(diffSecs / 60)}m ago`;
	const hours = Math.floor(diffSecs / 3600);
	const mins = Math.floor((diffSecs % 3600) / 60);
	return `${hours}h ${mins}m ago`;
}
