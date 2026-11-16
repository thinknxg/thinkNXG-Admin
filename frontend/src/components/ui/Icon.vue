<script setup lang="ts">
import { computed } from "vue";
import {
	Activity, IndentIncrease, IndentDecrease, ArrowDown, ArrowUp, ArrowDownRight, ArrowUpRight, Bell, Blocks, BookOpen, Building2, CalendarRange, ChartColumn, Check,
	ChevronDown, ChevronRight, ChevronsUpDown, CircleAlert, CircleCheck, CircleHelp, CircleX, Clock, Command, Contact,
	Database, ExternalLink, FileText, GitBranch, HardDrive, IdCard, Inbox, KeyRound, LayoutDashboard, LayoutGrid,
	LifeBuoy, ListChecks, LogOut, Menu, Monitor, Moon, Network, PanelLeft, PanelsTopLeft, Plug, Plus, RefreshCw,
	ScrollText, Search, Server, Settings, ShieldAlert, ShieldCheck, SlidersHorizontal, Sparkles, Star, Sun, Target,
	Terminal, Timer, TriangleAlert, User, UserRound, Users, Warehouse, Workflow, X, Cpu, Layers, Info, Circle,
	Briefcase, UsersRound, Landmark, ShoppingCart, ShoppingBag, Package, Factory, Handshake, FolderKanban, Box, BadgeCheck, ArrowLeftRight, Stamp, Receipt, Banknote, ClipboardList, Truck, UserPlus, UserSearch, CalendarCheck, Plane, Wallet, Route, Trophy, GraduationCap, CalendarPlus, MessagesSquare, LogIn, Filter, Calendar, Lock, House,
} from "lucide-vue-next";

const map: Record<string, any> = {
	activity: Activity, indent: IndentIncrease, outdent: IndentDecrease, "arrow-down": ArrowDown, "arrow-up": ArrowUp, "arrow-down-right": ArrowDownRight, "arrow-up-right": ArrowUpRight, bell: Bell, blocks: Blocks,
	"book-open": BookOpen, "building-2": Building2, "calendar-range": CalendarRange, "chart-column": ChartColumn,
	check: Check, "chevron-down": ChevronDown, "chevron-right": ChevronRight, "chevrons-up-down": ChevronsUpDown,
	"circle-alert": CircleAlert, "circle-check": CircleCheck, "circle-help": CircleHelp, "circle-x": CircleX,
	clock: Clock, command: Command, contact: Contact, database: Database, "external-link": ExternalLink,
	"file-text": FileText, "git-branch": GitBranch, "hard-drive": HardDrive, "id-card": IdCard, inbox: Inbox,
	"key-round": KeyRound, "layout-dashboard": LayoutDashboard, "layout-grid": LayoutGrid, "life-buoy": LifeBuoy,
	"list-checks": ListChecks, "log-out": LogOut, menu: Menu, monitor: Monitor, moon: Moon, network: Network,
	"panel-left": PanelLeft, "panels-top-left": PanelsTopLeft, plug: Plug, plus: Plus, "refresh-cw": RefreshCw,
	"scroll-text": ScrollText, search: Search, server: Server, settings: Settings, "shield-alert": ShieldAlert,
	"shield-check": ShieldCheck, "sliders-horizontal": SlidersHorizontal, sparkles: Sparkles, star: Star, sun: Sun,
	target: Target, terminal: Terminal, timer: Timer, "triangle-alert": TriangleAlert, user: User,
	"user-round": UserRound, users: Users, warehouse: Warehouse, workflow: Workflow, x: X, cpu: Cpu, layers: Layers,
	info: Info, circle: Circle, role: ShieldCheck,
	"briefcase": Briefcase, "users-round": UsersRound, "landmark": Landmark, "shopping-cart": ShoppingCart, "shopping-bag": ShoppingBag, "package": Package, "factory": Factory, "handshake": Handshake, "folder-kanban": FolderKanban, "box": Box, "badge-check": BadgeCheck, "arrow-left-right": ArrowLeftRight, "stamp": Stamp, "receipt": Receipt, "banknote": Banknote, "clipboard-list": ClipboardList, "truck": Truck, "user-plus": UserPlus, "user-search": UserSearch, "calendar-check": CalendarCheck, "plane": Plane, "wallet": Wallet, "route": Route, "trophy": Trophy, "graduation-cap": GraduationCap, "calendar-plus": CalendarPlus, "messages-square": MessagesSquare, "log-in": LogIn, "filter": Filter, "calendar": Calendar, "lock": Lock, "house": House,
};

const props = withDefaults(defineProps<{ name?: string; size?: number; strokeWidth?: number }>(), { size: 16, strokeWidth: 1.75 });
const component = computed(() => map[props.name || ""] || Circle);
</script>

<template>
	<component :is="component" :size="size" :stroke-width="strokeWidth" aria-hidden="true" class="shrink-0" />
</template>
