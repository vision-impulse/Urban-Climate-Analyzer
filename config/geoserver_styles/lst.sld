<?xml version="1.0" encoding="UTF-8"?>
<sld:StyledLayerDescriptor version="1.0.0"
    xsi:schemaLocation="http://www.opengis.net/sld StyledLayerDescriptor.xsd"
    xmlns:sld="http://www.opengis.net/sld"
    xmlns:ogc="http://www.opengis.net/ogc"
    xmlns:xlink="http://www.w3.org/1999/xlink"
    xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
    
  <sld:NamedLayer>
    <sld:Name>lst</sld:Name>
    <sld:UserStyle>
      <sld:Title>Turbo Colormap (0–1 range)</sld:Title>
      <sld:Abstract>Color ramp using Turbo for raster values 0 to 1</sld:Abstract>
      <sld:FeatureTypeStyle>
        <sld:Rule>
          <sld:RasterSymbolizer>
            <sld:ColorMap type="ramp">
              <sld:ColorMapEntry color="#30123b" quantity="0.00" label="0.00" opacity="1.0"/>
              <sld:ColorMapEntry color="#4149b5" quantity="0.10" label="0.10" opacity="1.0"/>
              <sld:ColorMapEntry color="#2c9bdc" quantity="0.20" label="0.20" opacity="1.0"/>
              <sld:ColorMapEntry color="#26c7b8" quantity="0.30" label="0.30" opacity="1.0"/>
              <sld:ColorMapEntry color="#61e574" quantity="0.40" label="0.40" opacity="1.0"/>
              <sld:ColorMapEntry color="#b4f01b" quantity="0.50" label="0.50" opacity="1.0"/>
              <sld:ColorMapEntry color="#ffd012" quantity="0.60" label="0.60" opacity="1.0"/>
              <sld:ColorMapEntry color="#ffa60b" quantity="0.70" label="0.70" opacity="1.0"/>
              <sld:ColorMapEntry color="#e75c0c" quantity="0.80" label="0.80" opacity="1.0"/>
              <sld:ColorMapEntry color="#9c220c" quantity="0.90" label="0.90" opacity="1.0"/>
              <sld:ColorMapEntry color="#6d0f14" quantity="1.00" label="1.00" opacity="1.0"/>
            </sld:ColorMap>
          </sld:RasterSymbolizer>
        </sld:Rule>
      </sld:FeatureTypeStyle>
    </sld:UserStyle>
  </sld:NamedLayer>
</sld:StyledLayerDescriptor>
