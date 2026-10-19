<?php
/**
 * Movies database credentials come from the environment or a private
 * movies-db-private.php file outside the document root. Hosts with a
 * virtual FTP root can use the HTTP-blocked .movies-db-private directory.
 */
function getMoviesPrivateConfigPath()
{
    $siteRoot = dirname(dirname(dirname(__FILE__)));
    $privatePath = dirname($siteRoot) . '/movies-db-private.php';
    if (!is_readable($privatePath) &&
        is_readable($siteRoot . '/.movies-db-private/.htaccess')) {
        $privatePath = $siteRoot . '/.movies-db-private/credentials.php';
    }
    return $privatePath;
}

function getMoviesTmdbApiKey()
{
    $key = getenv('TMDB_API_KEY');
    if ($key !== false && $key !== '') {
        return $key;
    }
    $privatePath = getMoviesPrivateConfigPath();
    if (is_readable($privatePath)) {
        $credentials = require $privatePath;
        if (is_array($credentials) && isset($credentials['tmdb_api_key']) &&
            is_string($credentials['tmdb_api_key']) &&
            $credentials['tmdb_api_key'] !== '') {
            return $credentials['tmdb_api_key'];
        }
    }
    error_log('Movies TMDB API key is not configured');
    return null;
}

function getDbConnection()
{
    $username = getenv('EJAGUIAR1_TVMOVIESTRAILERS_USER');
    $password = getenv('EJAGUIAR1_TVMOVIESTRAILERS_PASS');
    $hasUser = $username !== false && $username !== '';
    $hasPass = $password !== false && $password !== '';

    if ($hasUser || $hasPass) {
        if (!$hasUser || !$hasPass) {
            error_log('Movies DB environment credentials are incomplete');
            return null;
        }
    } else {
        $privatePath = getMoviesPrivateConfigPath();
        if (!is_readable($privatePath)) {
            error_log('Movies DB credentials are not configured');
            return null;
        }
        $credentials = require $privatePath;
        if (!is_array($credentials) ||
            !isset($credentials['username'], $credentials['password']) ||
            !is_string($credentials['username']) ||
            !is_string($credentials['password']) ||
            $credentials['username'] === '' ||
            $credentials['password'] === '') {
            error_log('Movies DB private configuration is invalid');
            return null;
        }
        $username = $credentials['username'];
        $password = $credentials['password'];
    }

    try {
        $pdo = new PDO(
            'mysql:host=localhost;dbname=ejaguiar1_tvmoviestrailers;charset=utf8mb4',
            $username,
            $password
        );
        $pdo->setAttribute(PDO::ATTR_ERRMODE, PDO::ERRMODE_EXCEPTION);
        $pdo->setAttribute(PDO::ATTR_DEFAULT_FETCH_MODE, PDO::FETCH_ASSOC);
        return $pdo;
    } catch (PDOException $e) {
        error_log('Movies DB connection failed (code ' . $e->getCode() . ')');
        return null;
    }
}
