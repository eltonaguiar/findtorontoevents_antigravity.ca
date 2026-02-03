/**
 * Direct Database Initialization
 * Executes schema.sql directly via MySQL connection
 */

const mysql = require('mysql2/promise');
const fs = require('fs').promises;
const path = require('path');

const DB_CONFIG = {
    host: 'localhost', // This will connect to the remote DB via their server
    user: 'ejaguiar1_tvmoviestrailers',
    password: 'tvmoviestrailers',
    database: 'ejaguiar1_tvmoviestrailers',
    multipleStatements: true
};

async function initializeDatabase() {
    let connection;

    try {
        console.log('🔗 Connecting to database...');
        console.log(`   Host: ${DB_CONFIG.host}`);
        console.log(`   Database: ${DB_CONFIG.database}`);
        console.log(`   User: ${DB_CONFIG.user}\n`);

        connection = await mysql.createConnection(DB_CONFIG);
        console.log('✅ Database connection successful!\n');

        // Read schema file
        const schemaPath = path.join(__dirname, '../database/schema.sql');
        console.log(`📖 Reading schema file: ${schemaPath}`);
        const schema = await fs.readFile(schemaPath, 'utf8');
        console.log(`✅ Schema file loaded (${schema.length} bytes)\n`);

        // Execute schema
        console.log('🔨 Creating database tables...');
        await connection.query(schema);
        console.log('✅ Schema executed successfully!\n');

        // Verify tables
        console.log('🔍 Verifying tables...\n');
        const [tables] = await connection.query('SHOW TABLES');

        console.log(`✅ Found ${tables.length} tables:`);
        tables.forEach(table => {
            const tableName = Object.values(table)[0];
            console.log(`   ✓ ${tableName}`);
        });

        // Get row counts
        console.log('\n📊 Table row counts:');
        for (const table of tables) {
            const tableName = Object.values(table)[0];
            const [result] = await connection.query(`SELECT COUNT(*) as count FROM ${tableName}`);
            console.log(`   ${tableName}: ${result[0].count} rows`);
        }

        console.log('\n✅ Database initialization complete!');

    } catch (error) {
        console.error('❌ Database initialization failed:', error.message);
        console.error('Full error:', error);
        throw error;
    } finally {
        if (connection) {
            await connection.end();
            console.log('\n🔌 Database connection closed');
        }
    }
}

// Run initialization
initializeDatabase()
    .then(() => {
        console.log('\n🎉 Success!');
        process.exit(0);
    })
    .catch(error => {
        console.error('\n💥 Failed:', error.message);
        process.exit(1);
    });
