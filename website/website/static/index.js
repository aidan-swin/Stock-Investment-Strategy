function deleteNote(noteId) {
    fetch('/delete-note',{
        method: "POST",
        body: JSON.stringify({ noteId: noteId}),  
    }).then((_res) => {
        window.location.href = "/";
    });
}

fetch('/percentage')
    .then(response => response.json())
    .then(data => {
        // Create the chart using Chart.js
        var ctx = document.getElementById('percentage-chart').getContext('2d');
        var chart = new Chart(ctx, {
            type: 'doughnut',
            data: {
                labels: ['Percentage'],
                datasets: [{
                    data: [data.percentage, 100 - data.percentage],
                    backgroundColor: ['#36a2eb', '#e9e9e9']
                }]
            },
            options: {
                cutoutPercentage: 70,
                responsive: true,
                maintainAspectRatio: false,
                tooltips: {
                    enabled: false
                },
                legend: {
                    display: false
                }
            }
        });
    });
    

