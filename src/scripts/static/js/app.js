function fetchStart(){
    fetch('/on').then(response => response.json()).then(function(data){
        console.log(data);
    });
}

function submit(){
    document.forms["dropdown-form"].submit();
}

function fetchStop(){
    fetch('/off').then(response => response.json()).then(function(data){
        console.log(data);
    });
}
