function fetchData() {
    const request = new XMLHttpRequest();
    request.open("GET", "https://0yme7vwsmc.execute-api.eu-central-1.amazonaws.com/get");
    request.setRequestHeader('authorization', 'website_temp');
    request.send();
    request.onload = () => {
        if (request.status === 200) {
            const data = JSON.parse(request.response);
            const temp = data[0].additional_data;
            const time = data[0].time.slice(0, -10);
            const tempElem = document.getElementById("tempHTML");
            const timeElem = document.getElementById("timeHTML");
            if (tempElem) tempElem.innerHTML = temp + " °C";
            if (timeElem) timeElem.innerHTML = time + " UTC";
        } else {
            console.log(`error ${request.status}`);
        }
    }
}

window.addEventListener('DOMContentLoaded', function() {
    fetchData();
    setInterval(fetchData, 300000);
});
   