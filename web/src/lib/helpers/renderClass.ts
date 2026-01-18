export function classColour(class_name: string): string {
	switch (class_name) {
		case 'C1':
			return 'text-cyan-400';
		case 'C2':
			return 'text-teal-400';
		case 'C3':
			return 'text-lime-400';
		case 'C4':
			return 'text-yellow-400';
		case 'C5':
			return 'text-orange-400';
		case 'C6':
			return 'text-red-400';
		case 'C13':
			return 'text-slate-400';
		case 'Thera':
			return 'text-slate-400';
		case 'Pochven':
			return 'text-orange-600';
		case 'Sentinel':
			return 'text-rose-400';
		case 'Barbican':
			return 'text-rose-400';
		case 'Vidette':
			return 'text-rose-400';
		case 'Redoubt':
			return 'text-rose-400';
		case 'Conflux':
			return 'text-rose-400';
		case 'HS':
			return 'text-green-500';
		case 'LS':
			return 'text-amber-600';
		case 'NS':
			return 'text-red-700';
		case 'Unknown':
			return 'text-surface-400';
		default:
			return 'text-gray-400';
	}
}

export function shouldShowSecStatus(class_name: string): boolean {
	return class_name === 'HS' || class_name === 'LS' || class_name === 'NS';
}

export function secStatusColour(secStatus?: number | null): string {
	if (!secStatus) {
		return 'text-slate-400';
	}
	if (secStatus >= 0.95) {
		return 'text-blue-600/80';
	} else if (secStatus >= 0.85) {
		return 'text-cyan-500/80';
	} else if (secStatus >= 0.75) {
		return 'text-emerald-500/80';
	} else if (secStatus >= 0.65) {
		return 'text-green-500/80';
	} else if (secStatus >= 0.55) {
		return 'text-lime-500/80';
	} else if (secStatus >= 0.45) {
		return 'text-yellow-400/80';
	} else if (secStatus >= 0.25) {
		return 'text-amber-600/80';
	} else if (secStatus >= 0.0) {
		return 'text-orange-600/80';
	} else {
		return 'text-red-700/80';
	}
}

export function secStatusBgColour(secStatus?: number | null): string {
	if (secStatus === undefined || secStatus === null) {
		return 'bg-slate-400';
	}
	if (secStatus >= 0.95) {
		return 'bg-blue-600';
	} else if (secStatus >= 0.85) {
		return 'bg-cyan-500';
	} else if (secStatus >= 0.75) {
		return 'bg-emerald-500';
	} else if (secStatus >= 0.65) {
		return 'bg-green-500';
	} else if (secStatus >= 0.55) {
		return 'bg-lime-500';
	} else if (secStatus >= 0.45) {
		return 'bg-yellow-400';
	} else if (secStatus >= 0.25) {
		return 'bg-amber-600';
	} else if (secStatus >= 0.0) {
		return 'bg-orange-600';
	} else {
		return 'bg-red-700';
	}
}

export function renderSecStatus(secStatus: number): string {
	return secStatus.toFixed(1);
}

export function isShattered(class_name: string, system_name: string): boolean {
	return (
		class_name === 'C13' ||
		class_name === 'Sentinel' ||
		class_name === 'Conflux' ||
		class_name === 'Barbican' ||
		class_name === 'Vidette' ||
		class_name === 'Redoubt' ||
		system_name.startsWith('J0')
	);
}

export function effectColour(effectName: string): string {
	switch (effectName) {
		case 'Black Hole':
			return 'text-gray-300';
		case 'Red Giant':
			return 'text-red-500/90';
		case 'Cataclysmic Variable':
			return 'text-yellow-200';
		case 'Pulsar':
			return 'text-sky-400';
		case 'Magnetar':
			return 'text-pink-500/90 ';
		case 'Wolf-Rayet Star':
			return 'text-amber-500';
		default:
			return 'text-surface-500';
	}
}

export function classBgColour(class_name: string | null | undefined): string {
	if (!class_name) return 'bg-gray-500';
	switch (class_name) {
		case 'C1':
			return 'bg-cyan-400';
		case 'C2':
			return 'bg-teal-400';
		case 'C3':
			return 'bg-lime-400';
		case 'C4':
			return 'bg-yellow-400';
		case 'C5':
			return 'bg-orange-400';
		case 'C6':
			return 'bg-red-400';
		case 'C13':
			return 'bg-slate-400';
		case 'Thera':
			return 'bg-slate-400';
		case 'Pochven':
			return 'bg-orange-600';
		case 'Sentinel':
		case 'Barbican':
		case 'Vidette':
		case 'Redoubt':
		case 'Conflux':
			return 'bg-rose-400';
		case 'HS':
			return 'bg-green-500';
		case 'LS':
			return 'bg-amber-600';
		case 'NS':
			return 'bg-red-700';
		case 'Unknown':
			return 'bg-surface-400';
		default:
			return 'bg-gray-400';
	}
}

export function classBorderColour(class_name: string | null | undefined): string {
	if (!class_name) return 'border-gray-500';
	switch (class_name) {
		case 'C1':
			return 'border-cyan-400';
		case 'C2':
			return 'border-teal-400';
		case 'C3':
			return 'border-lime-400';
		case 'C4':
			return 'border-yellow-400';
		case 'C5':
			return 'border-orange-400';
		case 'C6':
			return 'border-red-400';
		case 'C13':
			return 'border-slate-400';
		case 'Thera':
			return 'border-slate-400';
		case 'Pochven':
			return 'border-orange-600';
		case 'Sentinel':
		case 'Barbican':
		case 'Vidette':
		case 'Redoubt':
		case 'Conflux':
			return 'border-rose-400';
		case 'HS':
			return 'border-green-500';
		case 'LS':
			return 'border-amber-600';
		case 'NS':
			return 'border-red-700';
		case 'Unknown':
			return 'border-surface-400';
		default:
			return 'border-gray-400';
	}
}
