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

function gen_minidump_count_chart(element_id) {
    function gen_chart(data) {
        Chart.register(ChartDataLabels);
        let ctx = document.getElementById(element_id).getContext('2d');
        let chart = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: data["labels"],
                datasets: [{
                    data: data["counts"],
                    backgroundColor: 'rgba(54, 162, 235, 1)',
                    borderColor: 'rgba(0, 0, 0, 0.2)',
                    borderWidth: 1
                }]
            },
            plugins: [ChartDataLabels],
            options: {
                responsive: true,
                legend: {display: false, onClick: (e) => e.stopPropagation()},
                animation: false,
                maintainAspectRatio: false,
                plugins: {
                    datalabels: {
                        color: '#000',
                        font: {size: 20}
                    },
                    title: {display: true, text: 'Minidumps uploaded each day'},
                    legend: {display: false},
                    tooltip: {enabled: false}
                }
            },
        });
    }

    // Get Crash Data
    fetch("/webapi/stats/crash-per-day")
        .then(data => data.json())
        .then(json => gen_chart(json))
}

function get_attachment_contents(attachment_id){
    function present_contents(contents){
        // Remove loading spinner, remove onclick action, set code content, tell prism to process new content
        document.getElementById("file_button_" + attachment_id).removeAttribute("onclick");
        document.getElementById("file_loader_" + attachment_id).remove();
        document.getElementById("file_code_" + attachment_id).innerHTML = contents;
        let pre = document.getElementById("file_pre_" + attachment_id);
        pre.classList.remove("d-none");
        Prism.highlightAllUnder(pre);
    }

    fetch("/webapi/attachment/get-content/" + attachment_id)
        .then(data => data.json())
        .then(json => present_contents(json["file_content"]));
}