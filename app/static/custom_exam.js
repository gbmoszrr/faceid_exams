function all(){
    alert("I am an alert box!");
}


function ShowCamExam() {
    Webcam.set({
        width: 241,
        height: 181,
        image_format: 'jpeg',
        jpeg_quality: 90
    });
    Webcam.attach('#my_camera_exam'); 
    setInterval(getuserstatus, 15000);
}


// bind loadForm() and ShowCam() functions to the corresponding events
//window.addEventListener("DOMContentLoaded", loadForm);
window.addEventListener("load", ShowCamExam);

var cam_photo;

function snap() {
    Webcam.snap( function(data_uri) {
        
        document.getElementById('statusmessage').innerHTML = "Processing...";
        cam_photo =  data_uri;
    })
}

function getuserstatus() {
    //var photo = document.getElementById('image').src;
    snap();
    var form = document.getElementById('statusForm');
    photo = dataURItoBlob(cam_photo)
    var formData = new FormData(form);
    formData.append("file", photo);
    var xmlhttp = new XMLHttpRequest();
    xmlhttp.onreadystatechange = function()
        {
          if(this.readyState == 4 && this.status == 200) {
            document.getElementById('statusmessage').innerHTML = this.responseText;

            if(this.responseText.search('has been logged out') > 0 ) {
                window.location.href = '/';
            }

            if(this.responseText.search('not recognized') > 0 ) {
                $("#userstatus").removeClass("gooduser").addClass("wronguser");
            }
            else{
                $("#userstatus").removeClass("wronguser").addClass("gooduser");
            }
             
          } else {
            // document.getElementById('userstatus').innerHTML = "Error: camera error";
          }
        } 
    xmlhttp.open("POST", "/user/status/", false);
    xmlhttp.send(formData);    
}

function dataURItoBlob(dataURI) {
    // convert base64/URLEncoded data component to raw binary data held in a string
    var byteString;
    if (dataURI.split(',')[0].indexOf('base64') >= 0)
        byteString = atob(dataURI.split(',')[1]);
    else
        byteString = unescape(dataURI.split(',')[1]);

    // separate out the mime component
    var mimeString = dataURI.split(',')[0].split(':')[1].split(';')[0];

    // write the bytes of the string to a typed array
    var ia = new Uint8Array(byteString.length);
    for (var i = 0; i < byteString.length; i++) {
        ia[i] = byteString.charCodeAt(i);
    }
    return new Blob([ia], {type:mimeString});
}


