$(document).ready(function () {

    function handleJump() {
        $.ajax({
            url: '/flappybird-jump',
            type: 'POST',
            error: function (xhr, status, error) {
                console.error("Error sending direction:", error);
            }
        });
    }

    $(document).keydown(function (e) {
        console.log(e.which);

        switch (e.which) {
            case 32:
                handleJump();
                break;
            default: return;
        }
    });

})