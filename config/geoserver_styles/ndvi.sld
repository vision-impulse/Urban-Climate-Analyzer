<?xml version="1.0" encoding="UTF-8"?>
<StyledLayerDescriptor version="1.0.0"
    xsi:schemaLocation="http://www.opengis.net/sld StyledLayerDescriptor.xsd"
    xmlns="http://www.opengis.net/sld"
    xmlns:ogc="http://www.opengis.net/ogc"
    xmlns:xlink="http://www.w3.org/1999/xlink"
    xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
    
  <NamedLayer>
    <Name>ndvi</Name>
    <UserStyle>
      <Title>NDVI Green Ramp</Title>
      <Abstract>NDVI visualization from -1 to +1 using green shades</Abstract>
      <FeatureTypeStyle>
        <Rule>
          <RasterSymbolizer>
            <ColorMap type="ramp">
              <!-- Non-vegetation / invalid NDVI -->
              <ColorMapEntry color="#D3D3D3" quantity="-1.0" label="No Vegetation" opacity="1.0"/>
              <ColorMapEntry color="#D3D3D3" quantity="0.0" label="Bare Soil or Water" opacity="1.0"/>
              
              <!-- Vegetation NDVI values (light to dark green) -->
              <ColorMapEntry color="#e5f5e0" quantity="0.1" label="Low NDVI"/>
              <ColorMapEntry color="#a1d99b" quantity="0.3"/>
              <ColorMapEntry color="#74c476" quantity="0.5"/>
              <ColorMapEntry color="#31a354" quantity="0.7"/>
              <ColorMapEntry color="#006d2c" quantity="0.9" label="High NDVI"/>
              <ColorMapEntry color="#00441b" quantity="1.0"/>
            </ColorMap>
          </RasterSymbolizer>
        </Rule>
      </FeatureTypeStyle>
    </UserStyle>
  </NamedLayer>
</StyledLayerDescriptor>
