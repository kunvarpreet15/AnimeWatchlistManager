CREATE TABLE USERS (



    user_id INT AUTO_INCREMENT PRIMARY KEY,

    username VARCHAR(50) NOT NULL UNIQUE,

    email VARCHAR(100) NOT NULL UNIQUE,

    password_hash VARCHAR(255) NOT NULL,

    created_at DATETIME DEFAULT CURRENT_TIMESTAMP

);

CREATE TABLE ANIME (

    anime_id INT AUTO_INCREMENT PRIMARY KEY,

    title VARCHAR(200) NOT NULL,

    type VARCHAR(50) NOT NULL,

    release_year INT,

    total_episodes INT,

    description TEXT,

    poster_url VARCHAR(255)

);

CREATE TABLE GENRE (

    genre_id INT AUTO_INCREMENT PRIMARY KEY,

    genre_name VARCHAR(100) NOT NULL UNIQUE

);

CREATE TABLE STUDIO (

    studio_id INT AUTO_INCREMENT PRIMARY KEY,

    studio_name VARCHAR(200) NOT NULL UNIQUE

);

CREATE TABLE ANIME_GENRE (

    anime_id INT NOT NULL,

    genre_id INT NOT NULL,

    PRIMARY KEY (anime_id, genre_id),

    FOREIGN KEY (anime_id) REFERENCES ANIME(anime_id)

        ON DELETE CASCADE ON UPDATE CASCADE,

    FOREIGN KEY (genre_id) REFERENCES GENRE(genre_id)

        ON DELETE CASCADE ON UPDATE CASCADE

);

CREATE TABLE ANIME_STUDIO (

    anime_id INT NOT NULL,

    studio_id INT NOT NULL,

    PRIMARY KEY (anime_id, studio_id),

    FOREIGN KEY (anime_id) REFERENCES ANIME(anime_id)

        ON DELETE CASCADE ON UPDATE CASCADE,

    FOREIGN KEY (studio_id) REFERENCES STUDIO(studio_id)

        ON DELETE CASCADE ON UPDATE CASCADE

);

CREATE TABLE WATCHLIST (

    watchlist_id INT AUTO_INCREMENT PRIMARY KEY,

    user_id INT NOT NULL,

    anime_id INT NOT NULL,

    status VARCHAR(30),

    episodes_watched INT,

    last_updated DATETIME DEFAULT CURRENT_TIMESTAMP

        ON UPDATE CURRENT_TIMESTAMP,

    FOREIGN KEY (user_id) REFERENCES USERS(user_id)

        ON DELETE CASCADE ON UPDATE CASCADE,

    FOREIGN KEY (anime_id) REFERENCES ANIME(anime_id)

        ON DELETE CASCADE ON UPDATE CASCADE

);

CREATE TABLE REVIEW (

    review_id INT AUTO_INCREMENT PRIMARY KEY,

    user_id INT NOT NULL,

    anime_id INT NOT NULL,

    rating INT,

    review_text TEXT,

    review_date DATETIME DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (user_id) REFERENCES USERS(user_id)

        ON DELETE CASCADE ON UPDATE CASCADE,

    FOREIGN KEY (anime_id) REFERENCES ANIME(anime_id)

        ON DELETE CASCADE ON UPDATE CASCADE

);



