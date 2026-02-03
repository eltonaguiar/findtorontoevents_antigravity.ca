/**
 * UPDATE #111: GraphQL API Layer
 * GraphQL schema and resolvers
 */

interface GraphQLContext {
    userId?: number;
    isAuthenticated: boolean;
}

/**
 * GraphQL Schema Definition
 */
export const typeDefs = `
  type Movie {
    id: ID!
    title: String!
    type: String!
    releaseYear: Int
    genre: String
    description: String
    thumbnail: String
    rating: Float
    trailerUrl: String
    createdAt: String!
  }

  type TVShow {
    id: ID!
    title: String!
    type: String!
    firstAirDate: String
    seasons: Int
    episodes: Int
    status: String
    genre: String
    description: String
    thumbnail: String
    rating: Float
  }

  type User {
    id: ID!
    email: String!
    name: String
    subscription: Subscription
    favorites: [Movie!]!
    watchHistory: [Movie!]!
  }

  type Subscription {
    id: ID!
    tier: String!
    status: String!
    startDate: String!
    endDate: String
  }

  type Query {
    # Movies
    movie(id: ID!): Movie
    movies(
      limit: Int = 20
      offset: Int = 0
      genre: String
      sortBy: String
    ): [Movie!]!
    
    # TV Shows
    tvShow(id: ID!): TVShow
    tvShows(
      limit: Int = 20
      offset: Int = 0
      genre: String
    ): [TVShow!]!
    
    # User
    me: User
    user(id: ID!): User
    
    # Search
    search(query: String!, type: String): [Movie!]!
  }

  type Mutation {
    # Favorites
    addToFavorites(movieId: ID!): Movie!
    removeFromFavorites(movieId: ID!): Boolean!
    
    # Watch History
    addToWatchHistory(movieId: ID!): Movie!
    
    # User
    updateProfile(name: String, email: String): User!
    
    # Subscription
    subscribe(planId: String!): Subscription!
    cancelSubscription: Boolean!
  }

  type Subscription {
    movieAdded: Movie!
    userUpdated(userId: ID!): User!
  }
`;

/**
 * GraphQL Resolvers
 */
export const resolvers = {
    Query: {
        movie: async (_: any, { id }: { id: string }, context: GraphQLContext) => {
            // In production, fetch from database
            return {
                id,
                title: 'Sample Movie',
                type: 'movie',
                releaseYear: 2024,
                genre: 'Action',
                rating: 8.5,
                createdAt: new Date().toISOString()
            };
        },

        movies: async (
            _: any,
            { limit, offset, genre, sortBy }: any,
            context: GraphQLContext
        ) => {
            // In production, fetch from database with filters
            return [];
        },

        tvShow: async (_: any, { id }: { id: string }, context: GraphQLContext) => {
            return {
                id,
                title: 'Sample TV Show',
                type: 'tv',
                seasons: 3,
                episodes: 30,
                status: 'returning'
            };
        },

        tvShows: async (_: any, { limit, offset, genre }: any, context: GraphQLContext) => {
            return [];
        },

        me: async (_: any, __: any, context: GraphQLContext) => {
            if (!context.isAuthenticated) {
                throw new Error('Not authenticated');
            }

            // Return current user
            return {
                id: context.userId,
                email: 'user@example.com',
                favorites: [],
                watchHistory: []
            };
        },

        search: async (_: any, { query, type }: any, context: GraphQLContext) => {
            // In production, perform full-text search
            return [];
        }
    },

    Mutation: {
        addToFavorites: async (
            _: any,
            { movieId }: { movieId: string },
            context: GraphQLContext
        ) => {
            if (!context.isAuthenticated) {
                throw new Error('Not authenticated');
            }

            // Add to favorites in database
            return {
                id: movieId,
                title: 'Favorited Movie',
                type: 'movie'
            };
        },

        removeFromFavorites: async (
            _: any,
            { movieId }: { movieId: string },
            context: GraphQLContext
        ) => {
            if (!context.isAuthenticated) {
                throw new Error('Not authenticated');
            }

            // Remove from favorites
            return true;
        },

        updateProfile: async (
            _: any,
            { name, email }: any,
            context: GraphQLContext
        ) => {
            if (!context.isAuthenticated) {
                throw new Error('Not authenticated');
            }

            // Update user profile
            return {
                id: context.userId,
                email: email || 'user@example.com',
                name: name || 'User'
            };
        },

        subscribe: async (
            _: any,
            { planId }: { planId: string },
            context: GraphQLContext
        ) => {
            if (!context.isAuthenticated) {
                throw new Error('Not authenticated');
            }

            // Create subscription
            return {
                id: 'sub_123',
                tier: planId,
                status: 'active',
                startDate: new Date().toISOString()
            };
        }
    }
};

/**
 * GraphQL Client Hook
 */
import { useState } from 'react';

export function useGraphQL() {
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<Error | null>(null);

    const query = async (queryString: string, variables?: any) => {
        setLoading(true);
        setError(null);

        try {
            const response = await fetch('/graphql', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    query: queryString,
                    variables
                })
            });

            const result = await response.json();

            if (result.errors) {
                throw new Error(result.errors[0].message);
            }

            return result.data;
        } catch (err) {
            setError(err instanceof Error ? err : new Error('GraphQL query failed'));
            throw err;
        } finally {
            setLoading(false);
        }
    };

    const mutate = async (mutation: string, variables?: any) => {
        return query(mutation, variables);
    };

    return { query, mutate, loading, error };
}
