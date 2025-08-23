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
  const [showPlates, setShowPlates] = useState(true);
  const plotRef = useRef(null);
  const animationRef = useRef(null);

  const fetchData = async () => {
    setLoading(true);
    setError('');
    
    try {
      const response = await fetch(import.meta.env.VITE_API_URL, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
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
      title: 'Earthquake Animation - World Map',
      geo: {
        projection: { type: 'natural earth' },
        showland: true, landcolor: 'lightgray',
        showocean: true, oceancolor: 'lightblue',
        coastlinecolor: 'gray', showframe: false
      },
      height: 600
    };

    await Plotly.newPlot(plotRef.current, traces, layout, { responsive: true }); // { responsive: true } it ensures that the map resizes correctly

    if (showPlates) await loadPlates();
  };

  const loadPlates = async () => {
    try {
      const response = await fetch('https://raw.githubusercontent.com/fraxen/tectonicplates/master/GeoJSON/PB2002_boundaries.json');
      const plateData = await response.json();
      
      const [lats, lons] = [[], []];
      
      plateData.features.forEach(feature => {
        const processCoords = (coords) => { // coords is an array of coordinates [[lon, lat], [lon, lat], ...]
          coords.forEach(coord => { lons.push(coord[0]); lats.push(coord[1]); }); 
          lons.push(null); lats.push(null); // After finishing one line (or segment), we push null to separate line segments in Plotly.
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
    
    const step = () => {
      setCurrentIndex(prev => {
        const next = prev + 1;
        if (next >= earthquakeData.length) {
          setIsPlaying(false);
          return prev;
        }
        updateMap(next);
        if (next < earthquakeData.length - 1) {
          animationRef.current = setTimeout(step, 500);
        } else {
          setIsPlaying(false);
        }
        return next;
      });
    };
    step();
  };

  const stop = () => {
    setIsPlaying(false);
    if (animationRef.current) clearTimeout(animationRef.current);
  };

  const reset = () => {
    stop();
    setCurrentIndex(0);
    updateMap(-1);
  };

  const togglePlates = () => {
    setShowPlates(!showPlates);
    if (plotRef.current) {
      Plotly.restyle(plotRef.current, { visible: !showPlates }, [1]);
      if (!showPlates && (!plotRef.current.data[1].lat || plotRef.current.data[1].lat.length === 0)) {
        loadPlates();
      }
    }
  };

  useEffect(() => {
    initMap();
    return () => animationRef.current && clearTimeout(animationRef.current);
  }, []);

  useEffect(() => {
    if (earthquakeData.length > 0 && !isPlaying) updateMap(currentIndex);
  }, [earthquakeData, currentIndex]);

  const styles = {
    container: { minHeight: '100vh', backgroundColor: '#f5f5f5', padding: '20px', fontFamily: 'Arial, sans-serif' },
    card: { backgroundColor: 'white', padding: '20px', borderRadius: '8px', boxShadow: '0 2px 4px rgba(0,0,0,0.1)', marginBottom: '20px', maxWidth: '1200px', margin: '0 auto 20px auto' },
    input: { padding: '8px 12px', border: '1px solid #ddd', borderRadius: '4px', marginRight: '10px' },
    btn: { padding: '8px 16px', border: 'none', borderRadius: '4px', cursor: 'pointer', marginRight: '10px', color: 'white' },
    error: { marginTop: '15px', padding: '10px', backgroundColor: '#f8d7da', color: '#721c24', border: '1px solid #f5c6cb', borderRadius: '4px' }
  };

  return (
    <div style={styles.container}>
      <h1 style={{textAlign: 'center', color: '#333', marginBottom: '30px'}}>Earthquake Visualization</h1>
      
      <div style={styles.card}>
        <h2>Date Range</h2>
        <input type="date" value={startDate} onChange={(e) => setStartDate(e.target.value)} style={styles.input} />
        <input type="date" value={endDate} onChange={(e) => setEndDate(e.target.value)} style={styles.input} />
        <button onClick={fetchData} disabled={loading} style={{...styles.btn, backgroundColor: '#007bff'}}>
          {loading ? 'Loading...' : 'Fetch Data'}
        </button>
        {error && <div style={styles.error}>{error}</div>}
      </div>

      {earthquakeData.length > 0 && (
        <div style={styles.card}>
          <h3>Controls ({earthquakeData.length} earthquakes)</h3>
          <button onClick={animate} disabled={isPlaying} style={{...styles.btn, backgroundColor: '#28a745', opacity: isPlaying ? 0.6 : 1}}>
            {isPlaying ? 'Playing...' : 'Start'}
          </button>
          <button onClick={stop} disabled={!isPlaying} style={{...styles.btn, backgroundColor: '#dc3545', opacity: !isPlaying ? 0.6 : 1}}>
            Stop
          </button>
          <button onClick={reset} disabled={isPlaying} style={{...styles.btn, backgroundColor: '#6c757d', opacity: isPlaying ? 0.6 : 1}}>
            Reset
          </button>
          <button onClick={togglePlates} style={{...styles.btn, backgroundColor: showPlates ? '#17a2b8' : '#6c757d'}}>
            {showPlates ? 'Hide' : 'Show'} Plates
          </button>
          <div style={{marginTop: '10px', fontSize: '14px', color: '#666'}}>
            Showing: {Math.min(currentIndex + 1, earthquakeData.length)} / {earthquakeData.length}
          </div>
        </div>
      )}

      <div style={styles.card}>
        <div ref={plotRef} style={{width: '100%'}}></div>
      </div>
    </div>
  );
};

export default EarthquakeApp;