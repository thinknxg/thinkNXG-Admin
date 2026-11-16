frappe.ui.form.on("thinkNXG Admin Settings", {
	refresh(frm) {
		frm.add_custom_button(__("Open Command Center"), () => window.open("/thinknxg", "_self"));
	},
});
