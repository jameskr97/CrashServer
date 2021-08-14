function get_symbol_list(id){
    fetch("/webapi/symbols/" + id)
        .then(data => data.json())
        .then(data => document.getElementsByTagName('tbody')[0].innerHTML = data["html"])
}