function showAlert(message, type) {
    if (type==='success'){
        toastr.success(message);
    }
    else {
        if (type==="warning"){
            toastr.warning(message);
        }
        else {
            if (type==="info"){
                toastr.info(message);
            }
            else {
                if (type==="error"){
                    toastr.error(message);
                }
            }
        }
    }
}

function showLoading() {
    $('#divLoading').show();
}

function hideLoading() {
    $('#divLoading').hide();
}

function getDateStringFormatted(d) {
    return ("0" + d.getDate()).slice(-2) + "/" + ("0"+(d.getMonth()+1)).slice(-2) + "/" + d.getFullYear();
}

function getHourStringFormatted(d) {
    return ("0" + d.getHours()).slice(-2) + ":" + ("0" + d.getMinutes()).slice(-2);
}

document.addEventListener("DOMContentLoaded", function(){
    hideLoading();
});