function get_symbol_list(id){
    fetch("/webapi/symbols/" + id)
        .then(data => data.json())
        .then(data => document.getElementsByTagName('tbody')[0].innerHTML = data["html"])
}


function settings_registerEvents(){
    // Get all items of concern
    const contentAreas = [...document.getElementById("settings-content").getElementsByClassName("tab-pane")];
    const allTabs = document.querySelectorAll("#settings-top-tabs .nav-item, #settings-side-tabs a")

    const remove_active = (e) => e.classList.remove("active");
    const add_active = (e, id) => {if (e.id === id) e.classList.add("active")}

    // Register click event
    allTabs.forEach(e => e.addEventListener('click', function (){
        // Set and sync the tabs
        allTabs.forEach(e => remove_active(e));
        allTabs.forEach(e => add_active(e, this.id));

        // Set the content page
        contentAreas.forEach(e => remove_active(e))
        contentAreas.forEach(e => add_active(e, this.id + "-content"))
    }));
    // TODO(james): Deep linking with history modification
}