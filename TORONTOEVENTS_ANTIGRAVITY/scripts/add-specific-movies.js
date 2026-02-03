/**
 * Add specific movies to the database
 * Movies: The Housemaid, Zootopia, The Wrecking Crew, The Plague, Iron Lung, 
 *         Fallout, Wonderman, Anaconda, Greenland 2, The Rip, Shelter, Shrinking, Beauty
 */

const specificMovies = [
  {
    title: "The Housemaid",
    type: "movie",
    release_year: 2025,
    genre: "Thriller, Drama",
    description: "A psychological thriller about a housemaid with dark secrets",
    source: "manual_request"
  },
  {
    title: "Zootopia",
    type: "movie",
    release_year: 2016,
    genre: "Animation, Adventure, Comedy",
    description: "In a city of anthropomorphic animals, a rookie bunny cop and a cynical con artist fox must work together",
    source: "manual_request"
  },
  {
    title: "The Wrecking Crew",
    type: "movie",
    release_year: 2025,
    genre: "Action, Thriller",
    description: "An action-packed thriller about a demolition crew",
    source: "manual_request"
  },
  {
    title: "The Plague",
    type: "movie",
    release_year: 2025,
    genre: "Horror, Thriller",
    description: "A terrifying plague spreads through a small town",
    source: "manual_request"
  },
  {
    title: "Iron Lung",
    type: "movie",
    release_year: 2024,
    genre: "Horror, Sci-Fi",
    description: "Based on the horror game, a convict is sent to explore an ocean of blood",
    source: "manual_request"
  },
  {
    title: "Fallout",
    type: "tv_series",
    release_year: 2024,
    genre: "Sci-Fi, Action, Drama",
    description: "Based on the video game series, survivors emerge from underground vaults into a post-apocalyptic world",
    source: "manual_request"
  },
  {
    title: "Wonder Man",
    type: "tv_series",
    release_year: 2025,
    genre: "Action, Comedy, Superhero",
    description: "Marvel series about Simon Williams, a superhero with ionic energy powers",
    source: "manual_request"
  },
  {
    title: "Anaconda",
    type: "movie",
    release_year: 2025,
    genre: "Horror, Thriller",
    description: "A deadly giant anaconda terrorizes a group of explorers",
    source: "manual_request"
  },
  {
    title: "Greenland 2",
    type: "movie",
    release_year: 2025,
    genre: "Action, Thriller, Disaster",
    description: "Sequel to Greenland, continuing the survival story after a comet impact",
    source: "manual_request"
  },
  {
    title: "The Rip",
    type: "movie",
    release_year: 2025,
    genre: "Thriller, Mystery",
    description: "A mysterious thriller about a dangerous rip in reality",
    source: "manual_request"
  },
  {
    title: "Shelter",
    type: "movie",
    release_year: 2025,
    genre: "Drama, Thriller",
    description: "A gripping story about finding shelter in desperate times",
    source: "manual_request"
  },
  {
    title: "Shrinking",
    type: "tv_series",
    release_year: 2023,
    genre: "Comedy, Drama",
    description: "A grieving therapist starts to break the rules by telling his clients exactly what he thinks",
    source: "manual_request"
  },
  {
    title: "Beauty",
    type: "movie",
    release_year: 2025,
    genre: "Drama, Romance",
    description: "A powerful story exploring the concept of beauty and identity",
    source: "manual_request"
  }
];

async function addSpecificMovies() {
  const API_URL = 'https://findtorontoevents.ca/MOVIESHOWS/api/movies.php';
  
  console.log('Adding specific movies to database...\n');
  
  for (const movie of specificMovies) {
    try {
      const response = await fetch(API_URL, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(movie)
      });
      
      const result = await response.json();
      
      if (response.ok) {
        console.log(`✓ Added: ${movie.title} (ID: ${result.id})`);
      } else {
        console.error(`✗ Failed to add ${movie.title}: ${result.error}`);
      }
    } catch (error) {
      console.error(`✗ Error adding ${movie.title}:`, error.message);
    }
  }
  
  console.log('\nDone adding specific movies!');
}

// Run if executed directly
if (typeof require !== 'undefined' && require.main === module) {
  addSpecificMovies();
}

module.exports = { addSpecificMovies, specificMovies };
