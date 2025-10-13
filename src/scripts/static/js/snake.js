$(document).ready(function () {

    function sendSnakeDirection(direction) {
        console.log("Sending Request")
        $.ajax({
            url: '/snake-control',
            type: 'POST',
            data: {
                direction: direction
            },
            error: function (xhr, status, error) {
                console.error("Error sending direction:", error);
            }
        });
    }

    $('.direction-btn').click(function () {
        const direction = $(this).data('direction');
        sendSnakeDirection(direction);
    });

    $(document).keydown(function (e) {
        if (document.getElementById('snakeControlsModal').classList.contains('show')) {
            let direction = null;

            switch (e.which) {
                case 37: 
                    direction = 'LEFT';
                    break;
                case 38: 
                    direction = 'UP';
                    break;
                case 39: 
                    direction = 'RIGHT';
                    break;
                case 40: 
                    direction = 'DOWN';
                    break;
                default: return;
            }

            if (direction) {
                e.preventDefault();
                sendSnakeDirection(direction);
            }
        }
    });

    $('#reset-game').click(function () {
        $.ajax({
            url: '/snake-reset',
            type: 'POST',
            success: function (response) {
                $('#game-over-alert').addClass('d-none');
            },
            error: function (xhr, status, error) {
                showNotification('Error', 'Failed to reset game', 'error');
            }
        });
    });

    $('#snakeControlsModal').on('hidden.bs.modal', function () {
        if (snakeStatusInterval) {
            clearInterval(snakeStatusInterval);
        }
    });
})

let snakeStatusInterval;

function startSnakeStatusUpdates() {
    if (snakeStatusInterval) {
        clearInterval(snakeStatusInterval);
    }

    snakeStatusInterval = setInterval(function () {
        $.ajax({
            url: '/snake-status',
            type: 'GET',
            success: function (response) {
                $('#snake-score').text(response.score);

                if (response.game_over) {
                    $('#game-over-alert').removeClass('d-none');
                } else {
                    $('#game-over-alert').addClass('d-none');
                }
            },
            error: function (xhr, status, error) {
                console.error("Error getting snake status:", error);
                if (xhr.status === 400) {
                    clearInterval(snakeStatusInterval);
                }
            }
        });
    }, 500);
}
