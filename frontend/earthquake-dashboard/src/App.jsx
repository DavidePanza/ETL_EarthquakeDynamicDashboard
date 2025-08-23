import React, { useState, useRef, useEffect } from 'react';
import Plotly from 'plotly.js-dist';

const EarthquakeApp = () => {
  const [startDate, setStartDate] = useState('2025-08-17');
  const [endDate, setEndDate] = useState('2025-08-21');
  const [earthquakeData, setEarthquakeData] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [isPlaying, setIsPlaying] = useState(false);
  const [currentIndex, setCurrentIndex] = useState(0);
  const [showTectonicPlates, setShowTectonicPlates] = useState(true);
  const plotRef = useRef(null);
  const animationRef = useRef(null);

  const fetchEarthquakeData = async () => {
    setLoading(true);
    setError('');
    
    try {
      const response = await fetch(import.meta.env.VITE_API_URL, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          start_date: startDate,
          end_date: endDate
        })
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const responseData = await response.json();
      
      // Extract the data array from the response
      const data = responseData.data || [];
      
      // Sort earthquakes by full_time to show them in chronological order
      const sortedData = data.sort((a, b) => new Date(a.full_time) - new Date(b.full_time));
      setEarthquakeData(sortedData);
      setCurrentIndex(0);
      setIsPlaying(false);
      
    } catch (err) {
      setError(`Failed to fetch earthquake data: ${err.message}`);
      console.error('Error fetching data:', err);
    } finally {
      setLoading(false);
    }
  };

  const initializeMap = async () => {
    if (!plotRef.current) return;

    const layout = {
      title: {
        text: 'Earthquake Animation - World Map with Tectonic Plates',
        font: { size: 20 }
      },
      geo: {
        projection: { type: 'natural earth' },
        showland: true,
        landcolor: 'lightgray',
        showocean: true,
        oceancolor: 'lightblue',
        showlakes: true,
        lakecolor: 'lightblue',
        coastlinecolor: 'gray',
        showframe: false,
        bgcolor: 'white'
      },
      margin: { t: 60, b: 40, l: 40, r: 40 },
      height: 600
    };

    const earthquakeTrace = {
      type: 'scattergeo',
      mode: 'markers',
      lat: [],
      lon: [],
      text: [],
      marker: {
        size: [],
        color: 'red',
        opacity: 0.7,
        line: {
          color: 'darkred',
          width: 1
        }
      },
      name: 'Earthquakes'
    };

    // Tectonic plates trace (initially empty)
    const plateTrace = {
      type: 'scattergeo',
      mode: 'lines',
      lat: [],
      lon: [],
      line: {
        color: 'blue',
        width: 2,
        dash: 'dash'
      },
      showlegend: true,
      name: 'Tectonic Plate Boundaries',
      visible: showTectonicPlates
    };

    const traces = [earthquakeTrace, plateTrace];

    await Plotly.newPlot(plotRef.current, traces, layout, {
      responsive: true,
      displayModeBar: true
    });

    // Load tectonic plates data if enabled
    if (showTectonicPlates) {
      await loadTectonicPlates();
    }
  };

  const loadTectonicPlates = async () => {
    try {
      // Using a simplified tectonic plates dataset
      const response = await fetch('https://raw.githubusercontent.com/fraxen/tectonicplates/master/GeoJSON/PB2002_boundaries.json');
      const plateData = await response.json();
      
      const plateLats = [];
      const plateLons = [];
      
      // Process GeoJSON features
      plateData.features.forEach(feature => {
        if (feature.geometry.type === 'LineString') {
          // Add line coordinates
          feature.geometry.coordinates.forEach(coord => {
            plateLons.push(coord[0]);
            plateLats.push(coord[1]);
          });
          // Add null to separate line segments
          plateLons.push(null);
          plateLats.push(null);
        } else if (feature.geometry.type === 'MultiLineString') {
          // Handle multiple line strings
          feature.geometry.coordinates.forEach(lineString => {
            lineString.forEach(coord => {
              plateLons.push(coord[0]);
              plateLats.push(coord[1]);
            });
            // Add null to separate line segments
            plateLons.push(null);
            plateLats.push(null);
          });
        }
      });
      
      // Update the tectonic plates trace
      const update = {
        lat: [plateLats],
        lon: [plateLons]
      };
      
      Plotly.restyle(plotRef.current, update, [1]);
      
    } catch (error) {
      console.error('Failed to load tectonic plates data:', error);
    }
  };

  const toggleTectonicPlates = async () => {
    setShowTectonicPlates(!showTectonicPlates);
    
    if (plotRef.current) {
      // Toggle visibility of tectonic plates trace
      const update = {
        visible: !showTectonicPlates
      };
      Plotly.restyle(plotRef.current, update, [1]);
      
      // Load plates data if turning on and not already loaded
      if (!showTectonicPlates) {
        const currentData = plotRef.current.data[1];
        if (!currentData.lat || currentData.lat.length === 0) {
          await loadTectonicPlates();
        }
      }
    }
  };

  const updateMap = (index) => {
    if (!plotRef.current || !earthquakeData.length) return;

    const currentEarthquakes = earthquakeData.slice(0, index + 1);
    
    const lats = currentEarthquakes.map(eq => eq.latitude);
    const lons = currentEarthquakes.map(eq => eq.longitude);
    const sizes = currentEarthquakes.map(eq => Math.max(4, eq.mag * 3));
    const texts = currentEarthquakes.map(eq => 
      `Magnitude: ${eq.mag}<br>` +
      `Location: ${eq.place}<br>` +
      `Time: ${eq.full_time}<br>` +
      `Depth: ${eq.depth} km`
    );

    const update = {
      lat: [lats],
      lon: [lons],
      text: [texts],
      'marker.size': [sizes]
    };

    Plotly.restyle(plotRef.current, update, [0]);
  };

  const startAnimation = () => {
    if (!earthquakeData.length || isPlaying) return;
    
    setIsPlaying(true);
    setCurrentIndex(0);
    
    const animate = () => {
      setCurrentIndex(prevIndex => {
        const nextIndex = prevIndex + 1;
        
        if (nextIndex >= earthquakeData.length) {
          setIsPlaying(false);
          return prevIndex;
        }
        
        updateMap(nextIndex);
        
        if (nextIndex < earthquakeData.length - 1) {
          animationRef.current = setTimeout(animate, 500);
        } else {
          setIsPlaying(false);
        }
        
        return nextIndex;
      });
    };
    
    animate();
  };

  const stopAnimation = () => {
    setIsPlaying(false);
    if (animationRef.current) {
      clearTimeout(animationRef.current);
    }
  };

  const resetAnimation = () => {
    stopAnimation();
    setCurrentIndex(0);
    updateMap(-1);
  };

  useEffect(() => {
    initializeMap();
    
    return () => {
      if (animationRef.current) {
        clearTimeout(animationRef.current);
      }
    };
  }, []);

  useEffect(() => {
    if (earthquakeData.length > 0 && !isPlaying) {
      updateMap(currentIndex);
    }
  }, [earthquakeData, currentIndex]);

  const containerStyle = {
    minHeight: '100vh',
    backgroundColor: '#f5f5f5',
    padding: '20px',
    fontFamily: 'Arial, sans-serif'
  };

  const cardStyle = {
    backgroundColor: 'white',
    padding: '20px',
    borderRadius: '8px',
    boxShadow: '0 2px 4px rgba(0,0,0,0.1)',
    marginBottom: '20px',
    maxWidth: '1200px',
    margin: '0 auto 20px auto'
  };

  const inputStyle = {
    padding: '8px 12px',
    border: '1px solid #ddd',
    borderRadius: '4px',
    marginRight: '10px',
    marginBottom: '10px'
  };

  const buttonStyle = {
    padding: '8px 16px',
    border: 'none',
    borderRadius: '4px',
    cursor: 'pointer',
    marginRight: '10px',
    marginBottom: '10px'
  };

  const primaryButtonStyle = {
    ...buttonStyle,
    backgroundColor: '#007bff',
    color: 'white'
  };

  const successButtonStyle = {
    ...buttonStyle,
    backgroundColor: '#28a745',
    color: 'white'
  };

  const dangerButtonStyle = {
    ...buttonStyle,
    backgroundColor: '#dc3545',
    color: 'white'
  };

  const secondaryButtonStyle = {
    ...buttonStyle,
    backgroundColor: '#6c757d',
    color: 'white'
  };

  return (
    <div style={containerStyle}>
      <h1 style={{textAlign: 'center', color: '#333', marginBottom: '30px'}}>
        Earthquake Visualization Dashboard
      </h1>
      
      <div style={cardStyle}>
        <h2 style={{color: '#555', marginBottom: '15px'}}>Select Date Range</h2>
        <div>
          <label style={{marginRight: '10px'}}>Start Date: </label>
          <input
            type="date"
            value={startDate}
            onChange={(e) => setStartDate(e.target.value)}
            style={inputStyle}
          />
          
          <label style={{marginRight: '10px'}}>End Date: </label>
          <input
            type="date"
            value={endDate}
            onChange={(e) => setEndDate(e.target.value)}
            style={inputStyle}
          />
          
          <button
            onClick={fetchEarthquakeData}
            disabled={loading}
            style={primaryButtonStyle}
          >
            {loading ? 'Loading...' : 'Fetch Data'}
          </button>
        </div>
        
        {error && (
          <div style={{
            marginTop: '15px',
            padding: '10px',
            backgroundColor: '#f8d7da',
            color: '#721c24',
            border: '1px solid #f5c6cb',
            borderRadius: '4px'
          }}>
            {error}
          </div>
        )}
      </div>

      {earthquakeData.length > 0 && (
        <div style={cardStyle}>
          <h3 style={{color: '#555', marginBottom: '15px'}}>
            Animation Controls ({earthquakeData.length} earthquakes)
          </h3>
          <div>
            <button
              onClick={startAnimation}
              disabled={isPlaying}
              style={isPlaying ? {...successButtonStyle, opacity: 0.6} : successButtonStyle}
            >
              {isPlaying ? 'Playing...' : 'Start Animation'}
            </button>
            
            <button
              onClick={stopAnimation}
              disabled={!isPlaying}
              style={!isPlaying ? {...dangerButtonStyle, opacity: 0.6} : dangerButtonStyle}
            >
              Stop
            </button>
            
            <button
              onClick={resetAnimation}
              disabled={isPlaying}
              style={isPlaying ? {...secondaryButtonStyle, opacity: 0.6} : secondaryButtonStyle}
            >
              Reset
            </button>
            
            <button
              onClick={toggleTectonicPlates}
              style={{
                ...buttonStyle,
                backgroundColor: showTectonicPlates ? '#17a2b8' : '#6c757d',
                color: 'white'
              }}
            >
              {showTectonicPlates ? 'Hide' : 'Show'} Tectonic Plates
            </button>
          </div>
          
          <div style={{marginTop: '10px', fontSize: '14px', color: '#666'}}>
            Showing: {Math.min(currentIndex + 1, earthquakeData.length)} / {earthquakeData.length} earthquakes
          </div>
        </div>
      )}

      <div style={cardStyle}>
        <div ref={plotRef} style={{width: '100%'}}></div>
      </div>

      <div style={cardStyle}>
        <h3 style={{color: '#555', marginBottom: '10px'}}>Legend</h3>
        <p style={{fontSize: '14px', color: '#666', margin: 0}}>
          • <span style={{color: 'red'}}>Red circles</span>: Earthquakes (size = magnitude)<br/>
          • <span style={{color: 'blue'}}>Blue dashed lines</span>: Tectonic plate boundaries<br/>
          • Earthquakes appear chronologically during animation<br/>
          • Hover over markers to see detailed information
        </p>
      </div>
    </div>
  );
};

export default EarthquakeApp;