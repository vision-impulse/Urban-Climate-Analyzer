//VERSION=3
function setup() {
    return {
        input: [{
            bands: ["B04", "B08", "B11"]
        }],
        output: {
            id: "default",
            bands: 3,
            sampleType: SampleType.FLOAT32
        }
    };
}

function evaluatePixel(sample) {
    return [sample.B04, sample.B08, sample.B11]
}