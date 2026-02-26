import { useState, useMemo } from 'react';
import Map, { Source, Layer, NavigationControl } from 'react-map-gl';
import 'mapbox-gl/dist/mapbox-gl.css';

const MAPBOX_TOKEN = import.meta.env.VITE_MAPBOX_TOKEN;

// Styling for the polygon zones
const fillLayerStyle = {
    id: 'zones-fill',
    type: 'fill',
    paint: {
        'fill-color': '#088',
        'fill-opacity': [
            'case',
            ['boolean', ['feature-state', 'hover'], false],
            0.6,
            0.3
        ]
    }
};

const lineLayerStyle = {
    id: 'zones-line',
    type: 'line',
    paint: {
        'line-color': '#044',
        'line-width': 1
    }
};

export function ZoneMap({ zonesForLookup, onSelectZone }) {
    const [hoverInfo, setHoverInfo] = useState(null);

    // We are loading the big generated JSON.
    // We can fetch it or just tell Mapbox to load it from the public folder.
    const geojsonUrl = '/zones.geojson';

    // Find full zone detail when clicked
    const handleMapClick = (event) => {
        const feature = event.features && event.features[0];
        if (feature) {
            const zoneCode = feature.properties.zona;
            // Because the geojson might only have standard name/zone, let's find the full
            // zone object from the API list to pass down to analysis
            const matchedZone = zonesForLookup.find(z => z.zona === zoneCode) || { zona: zoneCode };
            onSelectZone(matchedZone);
        }
    };

    return (
        <div style={{ width: '100%', height: '100%', minHeight: '600px' }}>
            {!MAPBOX_TOKEN ? (
                <div style={{ padding: '2rem', textAlign: 'center' }}>Mapbox token is missing in .env</div>
            ) : (
                <Map
                    initialViewState={{
                        longitude: 12.5,
                        latitude: 42.5,
                        zoom: 5
                    }}
                    mapStyle="mapbox://styles/mapbox/light-v11"
                    mapboxAccessToken={MAPBOX_TOKEN}
                    interactiveLayerIds={['zones-fill']}
                    onClick={handleMapClick}
                    onMouseMove={(e) => {
                        const feature = e.features && e.features[0];
                        if (feature) {
                            setHoverInfo({
                                x: e.point.x,
                                y: e.point.y,
                                zone: feature.properties.zona
                            });
                        } else {
                            setHoverInfo(null);
                        }
                    }}
                    onMouseLeave={() => setHoverInfo(null)}
                >
                    <Source id="omi-zones" type="geojson" data={geojsonUrl} generateId={true}>
                        <Layer {...fillLayerStyle} />
                        <Layer {...lineLayerStyle} />
                    </Source>

                    <NavigationControl position="bottom-right" />

                    {hoverInfo && (
                        <div
                            style={{
                                position: 'absolute',
                                left: hoverInfo.x,
                                top: hoverInfo.y,
                                transform: 'translate(-50%, -100%)',
                                marginTop: '-10px',
                                background: 'white',
                                padding: '4px 8px',
                                borderRadius: '4px',
                                pointerEvents: 'none',
                                boxShadow: '0 1px 3px rgba(0,0,0,0.3)',
                                fontSize: '12px',
                                fontWeight: 'bold',
                                zIndex: 10
                            }}
                        >
                            Zone: {hoverInfo.zone}
                        </div>
                    )}
                </Map>
            )}
        </div>
    );
}
