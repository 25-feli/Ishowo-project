import React from 'react';

const Loader = () => {
    return (
        <div className="loader-container">
            <div className="loader-spinner"></div>
            <p className="loader-text">Chargement des données...</p>
        </div>
    );
};

export default Loader;