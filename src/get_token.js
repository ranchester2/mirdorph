let setRequestHeader = XMLHttpRequest.prototype.setRequestHeader
let isAuth = (key, value) => {
    return key == "Authorization" && value && !value.startsWith("Bearer");
}

XMLHttpRequest.prototype.setRequestHeader = function () {
    if (isAuth(arguments[0], arguments[1])) {
        window.location.href = "token://" + arguments[1]
        return
    }

    setRequestHeader.apply(this, arguments);
}