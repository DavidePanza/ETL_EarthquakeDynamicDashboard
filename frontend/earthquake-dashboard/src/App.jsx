import React, { useState, useRef, useEffect } from 'react';
import Plotly from 'plotly.js-dist';

const EarthquakeApp = () => {
  const [startDate, setStartDate] = useState('2025-08-20');
  const [endDate, setEndDate] = useState('2025-08-21');
  const [earthquakeData, setEarthquakeData] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [isPlaying, setIsPlaying] = useState(false);
  const [currentIndex, setCurrentIndex] = useState(0);
  const [showPlates, setShowPlates] = useState(true);
  const [animationSpeed, setAnimationSpeed] = useState(1); // 1x, 2x, 4x, 8x
  const plotRef = useRef(null);
  const animationRef = useRef(null);

  const fetchData = async () => {
    setLoading(true);
    setError('');
    
    try {
      const response = await fetch(import.meta.env.VITE_API_URL, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json',
                   'X-API-Key': import.meta.env.VITE_API_KEY  // Add this header
                 },
        body: JSON.stringify({ start_date: startDate, end_date: endDate })
      });

      if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
      
      const data = await response.json();
      const sortedData = (data.data || []).sort((a, b) => new Date(a.full_time) - new Date(b.full_time)); // (a,b) is needed as you deal with numbers
      setEarthquakeData(sortedData);
      setCurrentIndex(0); // index of the first earthquake to display
      setIsPlaying(false);
    } catch (err) {
      setError(`Failed to fetch data: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };

  const initMap = async () => {
    if (!plotRef.current) return;

    const traces = [
      {
        type: 'scattergeo',
        mode: 'markers',
        lat: [], lon: [], text: [],
        marker: { size: [], color: 'red', opacity: 0.7, line: { color: 'darkred', width: 1 } },
        name: 'Earthquakes'
      },
      {
        type: 'scattergeo',
        mode: 'lines',
        lat: [], lon: [],
        line: { color: 'blue', width: 2, dash: 'dash' },
        name: 'Tectonic Plates',
        visible: showPlates
      }
    ];

    const layout = {
      title: {
        text: 'Earthquake Animation - World Map',
        font: { size: 18, color: '#333' },
        x: 0.5
      },
      geo: {
        projection: { type: 'natural earth' },
        showland: true, landcolor: 'lightgray',
        showocean: true, oceancolor: 'lightblue',
        coastlinecolor: 'gray', showframe: false
      },
      height: 600,
      margin: { l: 40, r: 40, t: 60, b: 40 },
      showlegend: true,
      legend: {
        x: 0,
        y: 1.2,
        bgcolor: 'rgba(255,255,255,0.9)',
      }
    };

    await Plotly.newPlot(plotRef.current, traces, layout, { responsive: true, displayModeBar: true, modeBarButtonsToRemove: ['pan2d', 'select2d', 'lasso2d', 'autoScale2d'] }); // { responsive: true } it ensures that the map resizes correctly

    if (showPlates) await loadPlates();
  };

  const loadPlates = async () => {
    try {
      const response = await fetch('https://raw.githubusercontent.com/fraxen/tectonicplates/master/GeoJSON/PB2002_boundaries.json');
      const plateData = await response.json();
      
      const [lats, lons] = [[], []];
      
      plateData.features.forEach(feature => {
        const processCoords = (coords) => { // coords is an array of coordinates [[lon, lat], [lon, lat], ...]
          coords.forEach(coord => {
            lons.push(coord[0]);
            lats.push(coord[1]);
          });
          lons.push(null);
          lats.push(null); // After finishing one line (or segment), we push null to separate line segments in Plotly.
                           // In Plotly, arrays of coordinates with null values indicate a break in the line.
        };
        
        if (feature.geometry.type === 'LineString') {
          processCoords(feature.geometry.coordinates);
        } else if (feature.geometry.type === 'MultiLineString') {
          feature.geometry.coordinates.forEach(processCoords);
        }
      });

      Plotly.restyle(plotRef.current, { lat: [lats], lon: [lons] }, [1]); //[1] tells Plotly to update the second trace (tectonic plates)
    } catch (error) {
      console.error('Failed to load plates:', error);
    }
  };

  const updateMap = (index) => {
    if (!plotRef.current || !earthquakeData.length) return;

    const current = earthquakeData.slice(0, index + 1);
    const update = {
      lat: [current.map(eq => eq.latitude)], // Loops over an array and returns a new array with the results of the callback function (forEach does not return a new element)
      lon: [current.map(eq => eq.longitude)],
      text: [current.map(eq => `Mag: ${eq.mag}<br>Location: ${eq.place}<br>Time: ${eq.full_time}<br>Depth: ${eq.depth} km`)],
      'marker.size': [current.map(eq => Math.max(4, eq.mag * 3))]
    };

    Plotly.restyle(plotRef.current, update, [0]);
  };

  const animate = () => {
    if (!earthquakeData.length || isPlaying) return;
    setIsPlaying(true);
    setCurrentIndex(0);
  };

  const stop = () => {
    setIsPlaying(false);
    if (animationRef.current) {
      clearTimeout(animationRef.current);
      animationRef.current = null;
    }
    // Update map to show only earthquakes up to current index
    updateMap(currentIndex);
  };

  const reset = () => {
    stop();
    setCurrentIndex(0);
    updateMap(-1);
  };

  const togglePlates = () => {
    setShowPlates(!showPlates);
    if (plotRef.current) {
      Plotly.restyle(plotRef.current, { visible: !showPlates }, [1]); // visible: it shows or hide the tectonic plates
      if (!showPlates && (!plotRef.current.data[1].lat || plotRef.current.data[1].lat.length === 0)) {
        loadPlates();
      }
    }
  };

  useEffect(() => {
    initMap();
    return () => animationRef.current && clearTimeout(animationRef.current);
  }, []); // Initialize map and clear animation on unmount

  useEffect(() => { // shows the first earthquake on the map
    if (earthquakeData.length > 0 && !isPlaying) updateMap(currentIndex);
  }, [earthquakeData, currentIndex]);

  useEffect(() => {
    if (isPlaying && currentIndex < earthquakeData.length) {
      // Group earthquakes by hour
      const currentTime = new Date(earthquakeData[currentIndex]?.full_time);
      const currentHour = new Date(currentTime.getFullYear(), currentTime.getMonth(), currentTime.getDate(), currentTime.getHours());
      
      // Find all earthquakes in the same hour
      let nextIndex = currentIndex;
      while (nextIndex < earthquakeData.length) {
        const eqTime = new Date(earthquakeData[nextIndex].full_time);
        const eqHour = new Date(eqTime.getFullYear(), eqTime.getMonth(), eqTime.getDate(), eqTime.getHours());
        
        if (eqHour.getTime() === currentHour.getTime()) {
          nextIndex++;
        } else {
          break;
        }
      }
      
      updateMap(nextIndex - 1);
      
      if (nextIndex < earthquakeData.length) {
        animationRef.current = setTimeout(() => {
          setCurrentIndex(nextIndex);
        }, 500 / animationSpeed);
      } else {
        setIsPlaying(false);
      }
    }
  }, [currentIndex, isPlaying, earthquakeData, animationSpeed]);

  const styles = {
    container: { 
      minHeight: '100vh', 
      backgroundColor: '#f8f9fa', 
      padding: '20px', 
      font: 'Avenir sans-serif',
      // fontFamily: 'Inter, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif' 
    },
    card: { 
      backgroundColor: 'white', 
      padding: '24px', 
      borderRadius: '12px', 
      boxShadow: '0 4px 6px rgba(0,0,0,0.1)', 
      marginBottom: '24px', 
      maxWidth: '1000px', 
      margin: '0 auto 24px auto',
      border: '1px solid #e9ecef'
    },
    plotCard: { 
      backgroundColor: 'white', 
      padding: '24px', 
      borderRadius: '12px', 
      boxShadow: '0 4px 6px rgba(0,0,0,0.1)', 
      margin: '0 auto', 
      maxWidth: '1000px',
      border: '1px solid #e9ecef'
    },
    input: { 
      padding: '10px 12px', 
      border: '2px solid #e9ecef', 
      borderRadius: '6px', 
      marginRight: '12px',
      fontSize: '14px',
      transition: 'border-color 0.2s',
      outline: 'none'
    },
    btn: { 
      padding: '10px 18px', 
      border: 'none', 
      borderRadius: '6px', 
      cursor: 'pointer', 
      marginRight: '12px', 
      color: 'white',
      fontSize: '14px',
      fontWeight: '500',
      transition: 'all 0.2s',
      boxShadow: '0 2px 4px rgba(0,0,0,0.1)'
    },
    error: { 
      marginTop: '16px', 
      padding: '12px 16px', 
      backgroundColor: '#f8d7da', 
      color: '#721c24', 
      border: '1px solid #f5c6cb', 
      borderRadius: '6px',
      fontSize: '14px'
    },
    timeDisplay: {
      backgroundColor: '#f8f9fa',
      border: '2px solid #dee2e6',
      padding: '12px 20px',
      borderRadius: '8px',
      fontSize: '16px',
      fontWeight: '500',
      color: '#495057',
      boxShadow: '0 2px 4px rgba(0,0,0,0.05)'
    }
  };

  return (
    <div style={styles.container}>
      <h1 style={{textAlign: 'center', color: '#2c3e50', marginBottom: '40px', fontSize: '2.5rem', fontWeight: '600'}}>
        Earthquake Visualization
      </h1>
      
      <div style={styles.card}>
        <h2 style={{marginBottom: '20px', color: '#343a40', fontSize: '1.5rem'}}>Date Range</h2>
        <div style={{display: 'flex', alignItems: 'center', flexWrap: 'wrap', gap: '12px'}}>
          <input 
            type="date" 
            value={startDate} 
            onChange={(e) => setStartDate(e.target.value)} 
            style={styles.input}
          />
          <input 
            type="date" 
            value={endDate} 
            onChange={(e) => setEndDate(e.target.value)} 
            style={styles.input}
          />
          <button 
            onClick={fetchData} 
            disabled={loading} 
            style={{
              ...styles.btn, 
              backgroundColor: loading ? '#6c757d' : '#007bff',
              transform: loading ? 'none' : 'translateY(-1px)',
              cursor: loading ? 'not-allowed' : 'pointer'
            }}
          >
            {loading ? 'Loading...' : 'Fetch Data'}
          </button>
        </div>
        {error && <div style={styles.error}>{error}</div>}
      </div>

      {earthquakeData.length > 0 && (
        <div style={styles.card}>
          <h2 style={{marginBottom: '20px', color: '#343a40', fontSize: '1.5rem'}}>
            Controls
          </h2>
          <div style={{display: 'flex', alignItems: 'center', flexWrap: 'wrap', gap: '12px', marginBottom: '16px'}}>
            <button 
              onClick={animate} 
              disabled={isPlaying} 
              style={{
                ...styles.btn, 
                backgroundColor: '#28a745', 
                opacity: isPlaying ? 0.6 : 1,
                cursor: isPlaying ? 'not-allowed' : 'pointer'
              }}
            >
              {isPlaying ? 'Playing...' : 'Start'}
            </button>
            <button 
              onClick={stop} 
              disabled={!isPlaying} 
              style={{
                ...styles.btn, 
                backgroundColor: '#dc3545', 
                opacity: !isPlaying ? 0.6 : 1,
                cursor: !isPlaying ? 'not-allowed' : 'pointer'
              }}
            >
              Stop
            </button>
            <button 
              onClick={reset} 
              disabled={isPlaying} 
              style={{
                ...styles.btn, 
                backgroundColor: '#6c757d', 
                opacity: isPlaying ? 0.6 : 1,
                cursor: isPlaying ? 'not-allowed' : 'pointer'
              }}
            >
              Reset
            </button>
            <button 
              onClick={togglePlates} 
              style={{
                ...styles.btn, 
                backgroundColor: showPlates ? '#17a2b8' : '#6c757d'
              }}
            >
              {showPlates ? 'Hide' : 'Show'} Plates
            </button>
            <button 
              onClick={() => setAnimationSpeed(prev => prev >= 8 ? 1 : prev * 2)} 
              style={{
                ...styles.btn, 
                backgroundColor: '#ffc107', 
                color: '#212529'
              }}
            >
              Speed: {animationSpeed}x
            </button>
          </div>
          <div style={{fontSize: '14px', color: '#6c757d', fontWeight: '500'}}>
            Showing: <span style={{fontWeight: 'bold', color: '#495057'}}>{Math.min(currentIndex + 1, 
              earthquakeData.length)}</span> of <span style={{fontWeight: 'bold', color: '#495057'}}>{earthquakeData.length}</span>  earthquakes found
          </div>
        </div>
      )}

      <div style={styles.plotCard}>
        <div style={{ 
          display: 'flex', 
          flexDirection: 'column', 
          alignItems: 'center', 
          marginBottom: '24px'
        }}>
          <div style={{ 
            marginBottom: '12px', 
            fontSize: '16px', 
            fontWeight: '500', 
            color: '#495057' 
          }}>
            Current Earthquake Time:
          </div>
          <div style={styles.timeDisplay}>
            {earthquakeData[currentIndex]?.full_time || 'No data available'}
          </div>
        </div>
        <div ref={plotRef} style={{width: '100%'}}></div> {/* If you want React to "store" a DOM element inside a ref, you must attach it with the ref attribute. */}
      </div>
    </div>
  );
};

export default EarthquakeApp;