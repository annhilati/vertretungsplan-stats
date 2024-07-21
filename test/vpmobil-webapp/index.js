var txtList = [];

window.onload = function () {
  var tmpList = document.getElementsByClassName("bigContTxt");
  for (let i = 0; i < tmpList.length; i++) {
    const element = tmpList[i];
    if (element.id == "txt" + i.toString()) {
      txtList.push(element);
    }
  }
};

//Code, um die Informationen des heutigen Tages zu bekommen

function sendRequest() {
    myTok = document.getElementById("tokenInp").value
  fetch(
    "https://api.github.com/repos/annhilati/vertretungsplan-stats/contents/test/statTest.json?ref=main",
    {
      method: "GET",
      headers: {
        Authorization: `token ${myTok}`,
        Accept: "application/vnd.github.v3+json",
      },
    }
  )
    .then((response) => response.json())
    .then((data) => {
        const content = data.content;
        const parsedContent = JSON.parse(atob(content)); // Base64 dekodieren
        console.log(parsedContent);
        var data = parsedContent["dataList"]
        for (let index = 0; index < data.length; index++) {
            const element = data[index];
            txtList[index].innerText = element
        }
    })
    .catch((error) => console.error("Fehler:", error));
}
