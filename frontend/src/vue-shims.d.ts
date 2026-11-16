export {};
declare module "vue" {
	interface ComponentCustomProperties {
		/** Internal thinkNXG address for any link (old Desk addresses are translated). */
		$href: (href: string) => string;
	}
}
