//VERSION=3
function setup() {
    return {
        input: [{
            bands: ["B04", "B05", "B07", "B10"]
        }],
        output: {
            id: "default",
            bands: 4,
            sampleType: SampleType.FLOAT32
        }
    };
}

function evaluatePixel(sample) {
    return [sample.B04, sample.B05, sample.B07, sample.B10]
}
