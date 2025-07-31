<?xml version="1.0" encoding="UTF-8"?>
<StyledLayerDescriptor version="1.0.0"
    xsi:schemaLocation="http://www.opengis.net/sld StyledLayerDescriptor.xsd"
    xmlns="http://www.opengis.net/sld"
    xmlns:ogc="http://www.opengis.net/ogc"
    xmlns:xlink="http://www.w3.org/1999/xlink"
    xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
    
<NamedLayer>
  <Name>ndmi</Name>
  <UserStyle>
    <Title>NDMI Light Green Ramp</Title>
    <Abstract>NDMI visualization from -1 to +1 with soft green shades</Abstract>
    <FeatureTypeStyle>
      <Rule>
        <RasterSymbolizer>
          <ColorMap type="ramp">
            <!-- Dry or invalid NDMI values -->
            <ColorMapEntry color="#eeeeee" quantity="-1.0" label="Very Dry" opacity="1.0"/>
            <ColorMapEntry color="#dcdcdc" quantity="0.0" label="Neutral" opacity="1.0"/>

            <!-- Moisture (NDMI > 0) with light greenish ramp -->
            <ColorMapEntry color="#edf8e9" quantity="0.1" label="Low Moisture"/>
            <ColorMapEntry color="#bae4b3" quantity="0.3"/>
            <ColorMapEntry color="#a1d99b" quantity="0.5"/>
            <ColorMapEntry color="#74c476" quantity="0.7"/>
            <ColorMapEntry color="#41ab5d" quantity="0.9" label="High Moisture"/>
            <ColorMapEntry color="#238b45" quantity="1.0"/>
          </ColorMap>
        </RasterSymbolizer>
      </Rule>
    </FeatureTypeStyle>
  </UserStyle>
</NamedLayer>
</StyledLayerDescriptor>