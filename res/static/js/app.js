class SettingsUtil {
    static registerEvents() {
        // Get all items of concern
        const contentAreas = [...document.getElementById("settings-content").getElementsByClassName("tab-pane")];
        const allTabs = document.querySelectorAll("#settings-top-tabs .nav-item, #settings-side-tabs a")

        function settings_update_selected_tab(tab_id) {
            const remove_active = (e) => e.classList.remove("active");
            const add_active = (e, id) => {
                if (e.id === id) e.classList.add("active")
            }

            // Set and sync the tabs
            allTabs.forEach(e => remove_active(e));
            allTabs.forEach(e => add_active(e, tab_id));

            // Set the content page
            contentAreas.forEach(e => remove_active(e))
            contentAreas.forEach(e => add_active(e, tab_id + "-content"))
        }

        // Register click event
        allTabs.forEach(e => e.addEventListener('click', function () {
            settings_update_selected_tab(this.id)
        }));

        // TODO(james): Deep linking with history modification
        let url = location.href.replace(/\/$/, "");

        // Automatically preset a given tab if that tabs hash is in the url
        if (location.hash) {
            const hash = url.split("#")[1]
            settings_update_selected_tab(hash)
            history.replaceState(null, null, url);
        }
    }

    static registerTooltips(){
        var divs = document.getElementsByClassName("api-key-row")
        console.log(divs)
        for (let div of divs) {
            let button = div.getElementsByTagName("button")[0] // Should only be 1 button in here
            let tooltip = new bootstrap.Tooltip(button, {
                placement: 'right',
                trigger: 'click',
                title: 'Copied to clipboard'
            })
            button.addEventListener("click", () => setTimeout(() => tooltip.hide(), 2000));
        }
    }
}

class CrashServer {

    static toggleSidebar(){
        let sidebar = document.getElementById("sidebar")
        sidebar.hidden = !sidebar.hidden;
        document.cookie = "sidebar=" + (sidebar.hidden ? "true" : "") + ";path=/;";
    }

    static determineCurrentTheme() {
        let isLight = document.body.classList.contains("light-theme");
        let isDark = document.body.classList.contains("dark-theme");
        return (isLight || isDark) ? (isDark ? "dark-theme" : "light-theme") : "os-default";
    }

    static toggleDarkMode() {
        if (window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches) {
            document.body.classList.remove("dark-theme");
            document.body.classList.toggle("light-theme");
        } else {
            document.body.classList.remove("light-theme");
            document.body.classList.toggle("dark-theme");
        }

        let currentTheme = CrashServer.determineCurrentTheme();
        if (currentTheme !== "os-default") {
            document.cookie = "theme=" + currentTheme + ";path=/;";
        } else {
            document.cookie = "theme=;path=/;";
        }
    }

}

class CrashGraph {
    static genDefaultGraph(element_id, title, datapoints, labels) {
        let ctx = document.getElementById(element_id).getContext('2d');
        let chart = new Chart(ctx, {
            type: 'bar', data: {
                labels: labels, datasets: [{
                    data: datapoints, borderWidth: 1
                }]
            }, options: {
                responsive: true,
                legend: {display: false, onClick: (e) => e.stopPropagation()},
                animation: false,
                maintainAspectRatio: false,
                scales: {x: {grid: {display: false}}},
                barPercentage: 0.95,
                categoryPercentage: 1.0,
                plugins: {
                    datalabels: {
                        color: '#000', font: {size: 20}
                    }, title: {display: true, text: title}, legend: {display: false, labels: {font: {size: 200}}}, tooltip: {enabled: false}
                }
            },
        });

        function set_colors(isDark) {
            chart.data.datasets[0].backgroundColor = isDark ? '#DA0037' : 'rgba(54, 162, 235, 1)';
            chart.data.datasets[0].borderColor = isDark ? '#DA0037' : 'rgba(0, 0, 0, 0.2)';
            chart.options.scales['x'].grid.color = isDark ? '#ffffff66' : 'black';
            chart.options.scales['y'].grid.color = isDark ? '#ffffff66' : 'black';
            chart.update();
        }

        // Set to dark if the web browser prefers dark, and `determine_current_theme` results.
        set_colors((window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches && CrashServer.determineCurrentTheme() === "os-default") || CrashServer.determineCurrentTheme()  === "dark-theme");

        // Update dark website toggle on
        window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', e => {
            set_colors(e.matches);
        });

        // // Update dark/light graph on button press
        // document.getElementById("btn-toggle-dark").addEventListener("click", e => {
        //     let currentTheme = determine_current_theme()
        //
        //     if(currentTheme === "os-default") {
        //         set_colors(window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches);
        //     } else if(currentTheme === "dark-theme"){
        //         set_colors(true);
        //     } else {
        //         set_colors(false);
        //     }
        // });
        return chart
    }

    static genAllMinidumpCrashGraph(element_id, project_id) {
        fetch("/webapi/stats/crash-per-day/all?days=30")
            .then(data => data.json())
            .then(json => {
                let chart = CrashGraph.genDefaultGraph(element_id, 'Minidumps uploaded each day', json["counts"], json["labels"])
                chart.update()
                // Update graph content on select element change
                document.getElementById("chart-crash-day-select").addEventListener("change", e => {
                    // Get Crash Data
                    fetch("/webapi/stats/crash-per-day/all?days=" + e.target.value)
                        .then(data => data.json())
                        .then(json => {
                            chart.data.labels = json["labels"]
                            chart.data.datasets[0].data = json["counts"]
                            chart.update()
                        })
                })
            })
    }

    static genHomepageCrashGraph(element_id, project_id) {

        fetch("/webapi/stats/crash-per-day/" + project_id + "?days=30")
            .then(data => data.json())
            .then(json => {
                for (let i = 0; i < json["labels"].length; i++) {
                    json["labels"][i] = json["labels"][i][0]
                }
                let chart = CrashGraph.genDefaultGraph(element_id, 'Minidumps uploaded each day', json["counts"], json["labels"])
                // chart.options.scales['x'].ticks.display = false;
                chart.options.scales['x'].ticks.font = {size: 9}
                chart.update();
            })
    }

}

class CrashAPI {
    static getSymbolList(project_id){
        fetch("/webapi/symbols/" + project_id)
            .then(data => data.json())
            .then(data => document.getElementById("symbol-content-area").innerHTML = data["html"])
    }

    static deleteMinidump(minidump_id){
        fetch("/webapi/minidump/delete/" + minidump_id, {method: 'DELETE'})
            .then(data => window.location.reload(false))
    }

    static getAttachmentContents(attachment_id){
        function present_contents(contents) {
            // Remove loading spinner, remove onclick action, set code content, tell prism to process new content
            document.getElementById("file_button_" + attachment_id).removeAttribute("onclick");
            document.getElementById("file_loader_" + attachment_id).remove();
            document.getElementById("file_code_" + attachment_id).innerHTML = contents;
            let pre = document.getElementById("file_pre_" + attachment_id);
            pre.classList.remove("d-none");
            Prism.highlightAllUnder(pre);
        }

        function present_failed() {
            let spinner = document.getElementById("file_spinner_" + attachment_id)
            let msg = document.getElementById("file_msg_" + attachment_id)
            spinner.classList.remove(...spinner.classList);
            spinner.classList.add("fas", "fa-times-circle")
            msg.innerText = "Unable to load file contents."
        }

        fetch("/webapi/attachment/get-content/" + attachment_id)
            .then(response => {
                document.getElementById("file_button_" + attachment_id).removeAttribute("onclick");
                if (response.ok) {
                    return response.json()
                } else {
                    present_failed()
                    throw new Error("Unable to load attachment content for " + attachment_id)
                }
            })
            .then(json => present_contents(json["file_content"]));
    }
}
