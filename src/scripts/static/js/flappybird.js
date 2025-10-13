$(document).ready(function () {

    
    var socket = io('http://192.168.1.217:8000');

    $(document).keydown(function (e) {
        console.log(e.which);

        switch (e.which) {
            case 32:
                socket.emit('flappybird_jump')
                break;
            default: return;
        }
    });

})