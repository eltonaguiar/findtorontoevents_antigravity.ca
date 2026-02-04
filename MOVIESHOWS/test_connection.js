const mysql = require('mysql2/promise');

async function testConnection() {
    const configs = [
        { user: 'ejaguiar1_tvmoviestrailers', desc: 'Full database name as user' },
        { user: 'ejaguiar1', desc: 'Account prefix only' },
    ];

    for (const config of configs) {
        console.log(`\nTrying: ${config.desc}`);
        console.log(`User: ${config.user}`);

        try {
            const connection = await mysql.createConnection({
                host: 'mysql.50webs.com',
                user: config.user,
                password: 'virus2016',
                database: 'ejaguiar1_tvmoviestrailers',
                connectTimeout: 10000
            });

            console.log('✓ Connection successful!');

            const [tables] = await connection.query('SHOW TABLES');
            console.log('Tables:', tables);

            const [count] = await connection.query('SELECT COUNT(*) as total FROM movies');
            console.log(`Total movies: ${count[0].total}`);

            await connection.end();

            console.log('\n=== THIS CONFIG WORKS ===\n');
            break;

        } catch (error) {
            console.log(`✗ Failed: ${error.message}`);
        }
    }
}

testConnection().catch(console.error);
