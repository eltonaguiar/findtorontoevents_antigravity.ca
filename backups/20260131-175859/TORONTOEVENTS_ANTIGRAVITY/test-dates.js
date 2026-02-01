
const getTimeInToronto = (date) => {
    return new Intl.DateTimeFormat('en-CA', {
        timeZone: 'America/Toronto',
        year: 'numeric',
        month: '2-digit',
        day: '2-digit'
    }).format(date);
};

// Current local time from metadata: 2026-01-25T18:57:28-05:00
const now = new Date('2026-01-25T18:57:28-05:00');
console.log('Now in Toronto:', getTimeInToronto(now));

const eventDate1 = new Date('2026-01-25T12:00:00-05:00');
console.log('Event Jan 25 Noon in Toronto:', getTimeInToronto(eventDate1));
console.log('Is Today?', getTimeInToronto(eventDate1) === getTimeInToronto(now));

const eventDate2 = new Date('2026-01-26T12:00:00-05:00');
console.log('Event Jan 26 Noon in Toronto:', getTimeInToronto(eventDate2));
console.log('Is Tomorrow?', getTimeInToronto(eventDate2) === getTimeInToronto(new Date(now.getTime() + 24 * 60 * 60 * 1000)));
