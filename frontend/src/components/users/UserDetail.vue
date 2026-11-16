<script setup lang="ts">
import { computed, reactive, ref, watch } from "vue";
import { call, toast } from "frappe-ui";
import NxgDrawer from "@/components/ui/NxgDrawer.vue";
import NxgTabs from "@/components/ui/NxgTabs.vue";
import NxgAvatar from "@/components/ui/NxgAvatar.vue";
import NxgStatus from "@/components/ui/NxgStatus.vue";
import NxgMultiSelect from "@/components/ui/NxgMultiSelect.vue";
import NxgSwitch from "@/components/ui/NxgSwitch.vue";
import NxgDialog from "@/components/ui/NxgDialog.vue";
import Icon from "@/components/ui/Icon.vue";
import { errorMessage, runAction } from "@/data/api";
import { confirmAction } from "@/composables/useConfirm";
import { fmtDateTime, timeAgo } from "@/composables/format";

const props = defineProps<{ name: string | null; options: any }>();
const emit = defineEmits<{ close: []; changed: [] }>();
const API = "thinknxg_admin.api.users.";

const user = ref<any>(null);
const loading = ref(false);
const error = ref<string | null>(null);
const tab = ref("access");
const saving = ref(false);
const form = reactive({ roles: [] as string[], role_profiles: [] as string[], module_profile: "", default_workspace: "", default_app: "", enabled: true, user_type: "System User" });
const permForm = reactive({ open: false, allow: "Company", for_value: "", is_default: false });
const apiSecret = ref<{ key: string; secret: string } | null>(null);

async function load() {
	if (!props.name) return;
	loading.value = true;
	error.value = null;
	try {
		user.value = await call(API + "get_user", { name: props.name });
		reset();
	} catch (e) {
		error.value = errorMessage(e);
	} finally {
		loading.value = false;
	}
}
function reset() {
	const u = user.value;
	Object.assign(form, { roles: [...u.roles], role_profiles: [...u.role_profiles], module_profile: u.module_profile || "", default_workspace: u.default_workspace || "", default_app: u.default_app || "", enabled: !!u.enabled, user_type: u.user_type });
}
watch(() => props.name, (n) => { tab.value = "access"; apiSecret.value = null; n ? load() : (user.value = null); }, { immediate: true });

const dirty = computed(() => {
	const u = user.value;
	if (!u) return false;
	return JSON.stringify([...form.roles].sort()) !== JSON.stringify([...u.roles].sort()) || JSON.stringify(form.role_profiles) !== JSON.stringify(u.role_profiles) || form.module_profile !== (u.module_profile || "") || form.default_workspace !== (u.default_workspace || "") || form.default_app !== (u.default_app || "") || form.enabled !== !!u.enabled || form.user_type !== u.user_type;
});

async function save() {
	if (!form.enabled && user.value.enabled) {
		const ok = await confirmAction({ title: `Disable ${user.value.full_name}?`, message: "They will be signed out and unable to sign in until re-enabled.", confirmLabel: "Disable user", danger: true });
		if (!ok) return;
	}
	saving.value = true;
	const res = await runAction(API + "update_user", { name: props.name, values: { ...form } }, "User updated");
	saving.value = false;
	if (res) {
		user.value = res;
		reset();
		emit("changed");
	}
}
async function sendReset() {
	if (!(await confirmAction({ title: "Send password reset link?", message: `An email with a reset link goes to ${user.value.email}.`, confirmLabel: "Send link" }))) return;
	await runAction(API + "send_password_reset", { name: props.name }, "Reset link sent");
}
async function generateKeys() {
	const msg = user.value.has_api_key ? "This replaces the current API secret. Anything using the old secret stops working." : "An API key and secret will be created for this user.";
	if (!(await confirmAction({ title: user.value.has_api_key ? "Regenerate API secret?" : "Generate API access?", message: msg, confirmLabel: user.value.has_api_key ? "Regenerate" : "Generate", danger: user.value.has_api_key }))) return;
	try {
		// Core's own method (System Manager only). The secret is shown once and never stored here.
		const res: any = await call("frappe.core.doctype.user.user.generate_keys", { user: props.name });
		apiSecret.value = { key: res.api_key || user.value.api_key, secret: res.api_secret };
		await load();
	} catch (e) {
		toast.error(errorMessage(e));
	}
}
async function addPerm() {
	const res = await runAction(API + "add_user_permission", { user: props.name, allow: permForm.allow, for_value: permForm.for_value, is_default: permForm.is_default ? 1 : 0, apply_to_all_doctypes: 1 }, "User permission added");
	if (res) {
		permForm.open = false;
		permForm.for_value = "";
		load();
	}
}
async function removePerm(p: any) {
	if (!(await confirmAction({ title: "Remove this restriction?", message: `${p.allow}: ${p.for_value}`, confirmLabel: "Remove", danger: true }))) return;
	if (await runAction(API + "delete_user_permission", { name: p.name }, "Removed")) load();
}
function copy(text: string) {
	navigator.clipboard?.writeText(text).then(() => toast.success("Copied"));
}
const roleOptions = computed(() => (props.options?.roles || []).map((r: any) => r.name));
</script>

<template>
	<NxgDrawer :open="!!name" width="max-w-[620px]" @close="emit('close')">
		<template #header>
			<div v-if="user" class="flex items-center gap-3">
				<NxgAvatar :name="user.full_name" :image="user.user_image" :size="40" />
				<div class="min-w-0">
					<div class="flex items-center gap-2"><h2 class="truncate text-[16px] font-semibold">{{ user.full_name }}</h2><NxgStatus :status="user.enabled ? 'ok' : 'unknown'" :label="user.enabled ? 'Active' : 'Disabled'" /></div>
					<p class="truncate text-[12.5px] text-nxg-text-2">{{ user.email }} · {{ user.user_type }} · last sign-in {{ user.last_login ? timeAgo(user.last_login) : "never" }}</p>
				</div>
			</div>
			<div v-else class="nxg-skeleton h-10 w-60" />
		</template>

		<div v-if="error" class="p-5 text-[13px] text-nxg-danger">{{ error }}</div>
		<div v-else-if="loading && !user" class="space-y-3 p-5"><div v-for="i in 6" :key="i" class="nxg-skeleton h-6" /></div>
		<template v-else-if="user">
			<div class="px-5 pt-3"><NxgTabs v-model="tab" :tabs="[{ key: 'access', label: 'Access' }, { key: 'restrictions', label: 'Restrictions', count: user.user_permissions.length }, { key: 'security', label: 'Security' }, { key: 'activity', label: 'Activity' }]" /></div>

			<div v-if="tab === 'access'" class="space-y-5 p-5">
				<div class="flex items-center justify-between rounded-nxg border border-nxg-border px-3 py-2.5">
					<div><div class="text-[13px] font-medium">Account enabled</div><div class="text-[12px] text-nxg-text-2">{{ user.is_self ? "You can't disable your own account." : "Disabled users can't sign in." }}</div></div>
					<NxgSwitch v-model="form.enabled" label="Account enabled" :disabled="user.is_self" />
				</div>
				<div>
					<label class="nxg-label">User type</label>
					<select v-model="form.user_type" class="nxg-input"><option>System User</option><option>Website User</option></select>
				</div>
				<div>
					<label class="nxg-label">Role profiles <span class="font-normal text-nxg-text-3">· roles from profiles are applied by the framework on save</span></label>
					<NxgMultiSelect v-model="form.role_profiles" :options="options?.role_profiles || []" placeholder="Add profile" />
				</div>
				<div>
					<label class="nxg-label">Roles</label>
					<NxgMultiSelect v-model="form.roles" :options="roleOptions" placeholder="Add role" :locked="user.is_self ? ['System Manager'] : []" />
				</div>
				<div class="grid grid-cols-1 gap-4 sm:grid-cols-2">
					<div>
						<label class="nxg-label">Default workspace</label>
						<select v-model="form.default_workspace" class="nxg-input"><option value="">Not set</option><option v-for="w in options?.workspaces || []" :key="w.name" :value="w.name">{{ w.label || w.name }}</option></select>
					</div>
					<div>
						<label class="nxg-label">Default app</label>
						<select v-model="form.default_app" class="nxg-input"><option value="">Not set</option><option v-for="a in options?.apps || []" :key="a" :value="a">{{ a }}</option></select>
					</div>
					<div class="sm:col-span-2">
						<label class="nxg-label">Module profile <span class="font-normal text-nxg-text-3">· hides modules for this user</span></label>
						<select v-model="form.module_profile" class="nxg-input"><option value="">None</option><option v-for="m in options?.module_profiles || []" :key="m" :value="m">{{ m }}</option></select>
					</div>
				</div>
				<p class="text-[12px] text-nxg-text-3">Companies this user can see are set on the Restrictions tab (User Permissions on Company).</p>
			</div>

			<div v-else-if="tab === 'restrictions'" class="space-y-3 p-5">
				<p class="text-[12.5px] text-nxg-text-2">User Permissions limit which records this user sees, for example only one company. With none, access follows roles alone.</p>
				<ul class="divide-y divide-nxg-border rounded-nxg border border-nxg-border">
					<li v-for="p in user.user_permissions" :key="p.name" class="flex items-center gap-3 px-3 py-2 text-[13px]">
						<span class="nxg-chip">{{ p.allow }}</span>
						<span class="min-w-0 flex-1 truncate font-medium">{{ p.for_value }}</span>
						<span v-if="p.is_default" class="text-[11.5px] text-nxg-text-2">Default</span>
						<span class="text-[11.5px] text-nxg-text-3">{{ p.apply_to_all_doctypes ? "All documents" : `Only ${p.applicable_for}` }}</span>
						<button class="nxg-icon-btn h-7 w-7" :aria-label="`Remove ${p.allow} ${p.for_value}`" @click="removePerm(p)"><Icon name="x" :size="14" /></button>
					</li>
					<li v-if="!user.user_permissions.length" class="px-3 py-4 text-center text-[12.5px] text-nxg-text-2">No restrictions</li>
				</ul>
				<button class="nxg-btn nxg-btn-secondary" @click="permForm.open = true"><Icon name="plus" :size="14" />Add restriction</button>
			</div>

			<div v-else-if="tab === 'security'" class="space-y-3 p-5">
				<div class="flex items-center justify-between gap-3 rounded-nxg border border-nxg-border px-3 py-3">
					<div><div class="text-[13px] font-medium">Password</div><div class="text-[12px] text-nxg-text-2">Email the user a link to set a new password.</div></div>
					<button class="nxg-btn nxg-btn-secondary" :disabled="!user.enabled" @click="sendReset">Send reset link</button>
				</div>
				<div class="rounded-nxg border border-nxg-border px-3 py-3">
					<div class="flex items-center justify-between gap-3">
						<div><div class="text-[13px] font-medium">API access</div><div class="text-[12px] text-nxg-text-2">{{ user.has_api_key ? `Key ${user.api_key}` : "No API key issued" }}</div></div>
						<button class="nxg-btn nxg-btn-secondary" @click="generateKeys">{{ user.has_api_key ? "Regenerate secret" : "Generate keys" }}</button>
					</div>
					<div v-if="apiSecret" class="mt-3 rounded-nxg border border-[var(--nxg-warning)] bg-[var(--nxg-warning-soft)] p-3 text-[12.5px]">
						<p class="mb-2 font-medium">Copy the secret now. It won't be shown again.</p>
						<div class="flex items-center gap-2"><code class="min-w-0 flex-1 truncate rounded bg-nxg-surface px-2 py-1">{{ apiSecret.secret }}</code><button class="nxg-btn nxg-btn-secondary h-7" @click="copy(`token ${apiSecret.key}:${apiSecret.secret}`)">Copy token</button></div>
					</div>
				</div>
				<dl class="divide-y divide-nxg-border rounded-nxg border border-nxg-border text-[13px]">
					<div class="flex justify-between px-3 py-2"><dt class="text-nxg-text-2">Last IP</dt><dd class="nxg-tnum">{{ user.last_ip || "—" }}</dd></div>
					<div class="flex justify-between px-3 py-2"><dt class="text-nxg-text-2">Allowed sign-in hours</dt><dd>{{ user.login_after || user.login_before ? `${user.login_after ?? 0}:00 – ${user.login_before ?? 24}:00` : "Any time" }}</dd></div>
					<div class="flex justify-between px-3 py-2"><dt class="text-nxg-text-2">IP restriction</dt><dd class="truncate pl-4">{{ user.restrict_ip || "None" }}</dd></div>
					<div class="flex justify-between px-3 py-2"><dt class="text-nxg-text-2">Created</dt><dd>{{ fmtDateTime(user.creation) }}</dd></div>
				</dl>
				<a :href="`/thinknxg/admin/doc/user/${encodeURIComponent(user.name)}`" class="nxg-btn nxg-btn-ghost">Open full record<Icon name="chevron-right" :size="13" /></a>
			</div>

			<div v-else class="space-y-5 p-5">
				<div>
					<h3 class="mb-1.5 nxg-micro">Sign-in history</h3>
					<ul class="divide-y divide-nxg-border text-[13px]">
						<li v-for="l in user.logins" :key="l.name" class="flex items-center gap-2 py-1.5">
							<NxgStatus :status="l.status === 'Failed' ? 'failed' : 'success'" :label="l.operation === 'Logout' ? 'Signed out' : l.status === 'Failed' ? 'Failed' : 'Signed in'" />
							<span class="nxg-tnum flex-1 text-nxg-text-3">{{ l.ip_address }}</span>
							<span class="text-nxg-text-2" :title="fmtDateTime(l.creation)">{{ timeAgo(l.creation) }}</span>
						</li>
						<li v-if="!user.logins.length" class="py-3 text-nxg-text-2">No sign-ins recorded.</li>
					</ul>
				</div>
				<div>
					<h3 class="mb-1.5 nxg-micro">Recent changes made by this user</h3>
					<ul class="divide-y divide-nxg-border text-[13px]">
						<li v-for="v in user.recent_changes" :key="v.name" class="flex items-center justify-between gap-2 py-1.5"><a :href="$href(`/desk/${v.ref_doctype.toLowerCase().replace(/ /g, '-')}/${encodeURIComponent(v.docname)}`)" class="nxg-link truncate">{{ v.ref_doctype }} · {{ v.docname }}</a><span class="shrink-0 text-nxg-text-2">{{ timeAgo(v.creation) }}</span></li>
						<li v-if="!user.recent_changes.length" class="py-3 text-nxg-text-2">No tracked changes.</li>
					</ul>
				</div>
			</div>
		</template>

		<template v-if="user && tab === 'access'" #footer>
			<button class="nxg-btn nxg-btn-ghost" :disabled="!dirty" @click="reset">Discard</button>
			<button class="nxg-btn nxg-btn-primary" :disabled="!dirty || saving" @click="save">{{ saving ? "Saving…" : "Save changes" }}</button>
		</template>
	</NxgDrawer>

	<NxgDialog :open="permForm.open" title="Add restriction" description="Limit this user to one record of a DocType, for example one Company." @close="permForm.open = false">
		<div class="space-y-3 pb-2">
			<div><label class="nxg-label">Restrict by</label><input v-model="permForm.allow" class="nxg-input" placeholder="DocType, e.g. Company" /></div>
			<div>
				<label class="nxg-label">Value</label>
				<select v-if="permForm.allow === 'Company' && options?.companies?.length" v-model="permForm.for_value" class="nxg-input"><option value="" disabled>Choose a company</option><option v-for="c in options.companies" :key="c">{{ c }}</option></select>
				<input v-else v-model="permForm.for_value" class="nxg-input" placeholder="Record name" />
			</div>
			<label class="flex items-center gap-2 text-[13px]"><input v-model="permForm.is_default" type="checkbox" class="rounded border-nxg-border-strong text-nxg-espresso focus:ring-0" />Use as the user's default</label>
		</div>
		<template #footer>
			<button class="nxg-btn nxg-btn-secondary" @click="permForm.open = false">Cancel</button>
			<button class="nxg-btn nxg-btn-primary" :disabled="!permForm.allow || !permForm.for_value" @click="addPerm">Add</button>
		</template>
	</NxgDialog>
</template>
