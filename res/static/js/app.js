function update_symbol_list(id){
    fetch("/webapi/symbols/" + id)
        .then(data => data.json())
        .then(data => document.getElementById("symbol-content-area").innerHTML = data["html"])
}

function settings_registerEvents(){
    // Get all items of concern
    const contentAreas = [...document.getElementById("settings-content").getElementsByClassName("tab-pane")];
    const allTabs = document.querySelectorAll("#settings-top-tabs .nav-item, #settings-side-tabs a")

    function settings_update_selected_tab(tab_id){
            const remove_active = (e) => e.classList.remove("active");
            const add_active = (e, id) => {if (e.id === id) e.classList.add("active")}

            // Set and sync the tabs
            allTabs.forEach(e => remove_active(e));
            allTabs.forEach(e => add_active(e, tab_id));

            // Set the content page
            contentAreas.forEach(e => remove_active(e))
            contentAreas.forEach(e => add_active(e, tab_id + "-content"))
    }

    // Register click event
    allTabs.forEach(e => e.addEventListener('click', function (){
        settings_update_selected_tab(this.id)
    }));

    // TODO(james): Deep linking with history modification
    let url = location.href.replace(/\/$/, "");

    // Automatically preset a given tab if that tabs hash is in the url
    if(location.hash){
        const hash = url.split("#")[1]
        settings_update_selected_tab(hash)
        history.replaceState(null, null, url);
    }


}

function set_minidump_upload_enabled(bool){
    document.getElementById("minidump-upload").disabled = !bool;
}

function delete_minidump(id){
    fetch("/webapi/minidump/delete/" + id, {method: 'DELETE'})
        .then(data => window.location.reload(false))

}
