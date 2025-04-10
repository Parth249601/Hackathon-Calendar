document.addEventListener('DOMContentLoaded', function() {
    var calendarEl = document.getElementById('calendar');
    var eventDetailsEl = document.getElementById('event-details');
    var closeEventDetailsBtn = document.getElementById('close-event-details');
    var loadingSpinnerEl = document.getElementById('loading-spinner');
    var currentView = 'hackathons'; // Default to hackathons
    var calendar;
    var allEvents = []; // Store all events data
    
    // Show loading spinner, hide calendar initially
    showLoading(true);
    
    // Fetch all events data once
    fetchAllEvents().then(() => {
        // Initialize calendar with hackathons events
        updateCalendarView('hackathons');
        // Hide loading spinner, show calendar
        showLoading(false);
    }).catch(error => {
        // If there's an error, still hide spinner and show calendar (even if empty)
        console.error("Error loading calendar data:", error);
        showLoading(false);
        updateCalendarView('hackathons');
    });
    
    // Function to toggle loading state
    function showLoading(isLoading) {
        if (isLoading) {
            loadingSpinnerEl.classList.remove('d-none');
            calendarEl.classList.add('d-none');
        } else {
            loadingSpinnerEl.classList.add('d-none');
            calendarEl.classList.remove('d-none');
        }
    }
    
    // Function to fetch all events
    async function fetchAllEvents() {
        try {
            const response = await fetch('/api/all-events');
            if (!response.ok) {
                throw new Error('Network response was not ok');
            }
            allEvents = await response.json();
            console.log(`Loaded ${allEvents.length} events`);
        } catch (error) {
            console.error('Error fetching events:', error);
            allEvents = [];
        }
    }

    // Setup tabs
    const tabLinks = document.querySelectorAll('.nav-link');
    tabLinks.forEach(link => {
        link.addEventListener('click', function(e) {
            // Remove active class from all tabs
            tabLinks.forEach(tab => tab.classList.remove('active'));
            // Add active class to clicked tab
            this.classList.add('active');
            
            // Get view type from data attribute
            const viewType = this.getAttribute('data-type');
            updateCalendarView(viewType);
            
            // Update download buttons visibility
            document.querySelectorAll('.tab-pane').forEach(pane => {
                pane.classList.remove('show', 'active');
            });
            document.getElementById(`${viewType}-download`).classList.add('show', 'active');
        });
    });

    // Setup close button for event details
    closeEventDetailsBtn.addEventListener('click', function() {
        eventDetailsEl.classList.add('d-none');
    });

    function updateCalendarView(viewType) {
        currentView = viewType;
        if (calendar) {
            calendar.destroy(); // Destroy existing calendar
        }
        
        // Filter events based on the selected view
        let filteredEvents;
        switch(viewType) {
            case 'hackathons':
                filteredEvents = allEvents.filter(event => event.type === 'hackathon');
                break;
            case 'contests':
            default:
                filteredEvents = allEvents.filter(event => event.type === 'contest');
                break;
        }
        
        initCalendar(filteredEvents);
    }

    function initCalendar(events) {
        // Ensure events have proper display properties
        const formattedEvents = events.map(event => {
            // Make a copy of the event to avoid modifying original
            const formattedEvent = {...event};
            
            // Force block display style for all events
            formattedEvent.display = 'block';
            formattedEvent.allDay = true; // Make all events all-day to improve display
            
            // Set a reasonable title length
            if (formattedEvent.title && formattedEvent.title.length > 30) {
                formattedEvent.title = formattedEvent.title.substring(0, 30) + '...';
            }
            
            return formattedEvent;
        });
        
        calendar = new FullCalendar.Calendar(calendarEl, {
            initialView: 'dayGridMonth',
            headerToolbar: {
                left: 'prev,next today',
                center: 'title',
                right: 'dayGridMonth,timeGridWeek,timeGridDay'
            },
            events: formattedEvents, // Use the formatted events array
            eventClick: function(info) {
                // Show event details
                eventDetailsEl.classList.remove('d-none');
                
                // Update event details based on type
                updateEventDetails(info.event);
            },
            eventDidMount: function(info) {
                // Set event color based on type
                const eventType = info.event.extendedProps.type;
                if (eventType === 'contest') {
                    info.el.classList.add('contest-event');
                } else {
                    info.el.classList.add('hackathon-event');
                }
                
                // Add tooltip
                info.el.title = info.event.title;
                
                // Ensure the title is visible
                const titleEl = info.el.querySelector('.fc-event-title');
                if (titleEl) {
                    titleEl.style.display = 'block';
                    titleEl.style.fontWeight = '500';
                }
            },
            height: 'auto',
            eventTextColor: '#ffffff',
            eventTimeFormat: {
                hour: 'numeric',
                minute: '2-digit',
                meridiem: 'short'
            },
            dayMaxEvents: 6, // Show more events per day
            moreLinkClick: 'day', // Click on "more" goes to day view
            fixedWeekCount: false, // Only show the weeks in the current month
            showNonCurrentDates: false, // Hide days from other months
            eventDisplay: 'block', // Force block display for events
            displayEventTime: true, // Show event times
            displayEventEnd: true, // Show event end times
            eventMaxStack: 6, // Stack up to 6 events before showing "more" link
        });

        calendar.render();
    }
    
    function updateEventDetails(event) {
        // Common fields
        document.getElementById('event-name').textContent = event.title;
        document.getElementById('event-start').textContent = formatDateTime(event.start);
        document.getElementById('event-end').textContent = formatDateTime(event.end);
        document.getElementById('event-location').textContent = event.extendedProps.location || 'N/A';
        document.getElementById('event-prize').textContent = event.extendedProps.prize || 'N/A';
        document.getElementById('event-participants').textContent = event.extendedProps.participants || 'N/A';
        document.getElementById('event-platform').textContent = event.extendedProps.platform || 'N/A';
        
        // Set registration link (with fallback for Codeforces)
        const registerButton = document.getElementById('event-link');
        if (event.extendedProps.registration_link && event.extendedProps.registration_link !== "#") {
            registerButton.href = event.extendedProps.registration_link;
        } else if (event.extendedProps.platform === 'Codeforces') {
            // Default Codeforces URL if no specific link is available
            registerButton.href = 'https://codeforces.com/contests';
        } else {
            registerButton.href = '#';
        }
        
        // Type-specific fields
        const eventType = event.extendedProps.type;
        const durationContainer = document.getElementById('duration-container');
        const registrationTimes = document.getElementById('registration-times');
        const eventDetailsCard = document.getElementById('event-details');
        
        // Update card styling based on event type
        eventDetailsCard.classList.remove('hackathon-details', 'contest-details');
        registerButton.classList.remove('btn-primary', 'btn-success');
        
        if (eventType === 'contest') {
            // Show duration for CP contests
            durationContainer.classList.remove('d-none');
            document.getElementById('event-duration').textContent = event.extendedProps.duration || 'N/A';
            
            // For contests, explicitly show registration times
            registrationTimes.style.display = 'block';
            document.getElementById('event-reg-start').textContent = 
                formatDateTime(event.extendedProps.registration_start) || 'N/A';
            document.getElementById('event-reg-end').textContent = 
                formatDateTime(event.extendedProps.registration_end) || 'N/A';
                
            // Style for contests
            eventDetailsCard.classList.add('contest-details');
            registerButton.classList.add('btn-success');
            registerButton.textContent = 'View on Codeforces';
        } else {
            // Hide duration for hackathons
            durationContainer.classList.add('d-none');
            
            // For hackathons, the main start/end times are the registration times
            registrationTimes.style.display = 'none';
            
            // Style for hackathons
            eventDetailsCard.classList.add('hackathon-details');
            registerButton.classList.add('btn-primary');
            registerButton.textContent = 'Register';
        }
    }
    
    function formatDateTime(dateStr) {
        if (!dateStr) return 'N/A';
        return new Date(dateStr).toLocaleString();
    }
}); 