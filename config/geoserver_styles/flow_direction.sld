<?xml version="1.0" encoding="UTF-8"?><sld:StyledLayerDescriptor xmlns:sld="http://www.opengis.net/sld" xmlns="http://www.opengis.net/sld" xmlns:gml="http://www.opengis.net/gml" xmlns:ogc="http://www.opengis.net/ogc" version="1.0.0">
  <sld:NamedLayer>
    <sld:Name>Default Styler</sld:Name>
    <sld:UserStyle>
      <sld:Name>Default Styler</sld:Name>
      <sld:Title>D8 Flow Directions</sld:Title>
      <sld:FeatureTypeStyle>
        <sld:Name>flow_direction</sld:Name>
        <sld:Rule>
          <sld:Name>D89</sld:Name>
          <sld:PointSymbolizer>
            <sld:Graphic>
              <sld:ExternalGraphic>
                <sld:OnlineResource xmlns:xlink="http://www.w3.org/1999/xlink" xlink:type="simple" xlink:href="/styles/icons/arrow.svg"/>
                <sld:Format>image/svg+xml</sld:Format>
              </sld:ExternalGraphic>
              <sld:Size>12</sld:Size>
              <sld:Rotation>
                <ogc:Function name="Recode">
                  <ogc:PropertyName>direction</ogc:PropertyName>
                  <ogc:Literal>1</ogc:Literal>
                  <ogc:Literal>90</ogc:Literal>
                  <ogc:Literal>2</ogc:Literal>
                  <ogc:Literal>135</ogc:Literal>
                  <ogc:Literal>4</ogc:Literal>
                  <ogc:Literal>180</ogc:Literal>
                  <ogc:Literal>8</ogc:Literal>
                  <ogc:Literal>225</ogc:Literal>
                  <ogc:Literal>16</ogc:Literal>
                  <ogc:Literal>270</ogc:Literal>
                  <ogc:Literal>32</ogc:Literal>
                  <ogc:Literal>315</ogc:Literal>
                  <ogc:Literal>64</ogc:Literal>
                  <ogc:Literal>0</ogc:Literal>
                  <ogc:Literal>128</ogc:Literal>
                  <ogc:Literal>45</ogc:Literal>
                </ogc:Function>
              </sld:Rotation>
            </sld:Graphic>
          </sld:PointSymbolizer>
        </sld:Rule>
      </sld:FeatureTypeStyle>
    </sld:UserStyle>
  </sld:NamedLayer>
</sld:StyledLayerDescriptor>

