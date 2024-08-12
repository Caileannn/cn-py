function conicGradient(sA, cX, cY, colors) {
	let gradient = drawingContext.createConicGradient(
		sA, cX, cY
	);
	gradient.addColorStop(0, colors[0]);
	gradient.addColorStop(0.33, colors[1]);
	gradient.addColorStop(0.66, colors[2]);
	gradient.addColorStop(1, colors[0]);
	drawingContext.fillStyle = gradient;
}