<script lang="ts">
	import { Github } from 'lucide-svelte';
</script>

<footer class="flex items-center justify-between bg-black/75 px-8 py-2 backdrop-blur-2xl">
	<span class="text-xs text-surface-400">
		EVE Online and the EVE logo are trademarks of CCP hf.
	</span>
	<a
		href="https://github.com/ftsartek/linked"
		target="_blank"
		rel="noopener noreferrer"
		class="flex items-center gap-2 text-xs text-surface-400 hover:text-white"
	>
		<Github size={16} />
	</a>
</footer>
