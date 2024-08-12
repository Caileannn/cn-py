let myFont;
let data;
let geoArray = [];
let canvas;

var w, h, tow, toh;
var x, y, tox, toy;
var scaler = 1;
var exponent = 1;
var zoom = .01; //zoom step per mouse tick 


var wheel_scale = 0;
var drag_x = 0;
var drag_y = 0;
var e = 0;
var init_scale = 0.5;

var check_mouse = false;
var mouse_dragged = false;
var bar;

var scroll_height = 0;
var scroll_top = 0;
var percent = 0;

var current_text_seq, next_text_seq;
var direction = 0;

var mobile_view = false;
var network_view = false;
var about_view = false;

// Get the two button elements
const network_button = document.getElementById('network-button');
const text_button = document.getElementById('tv-button');

var text_view_padding = 100;


//let v1 = createVector(drag_x, drag_y);


// Load Data & Font
function preload() { 
  data = loadJSON('static/assets/data/data/sorted_output.json');
  myFont = loadFont('static/assets/data/assets/IBMPlexSans-Regular.ttf')
}

function setup() {
  if(window.innerWidth < 950){
    canvas = createCanvas(window.innerWidth, window.innerHeight);
    mobile_view = true;
	network_view = false
  }else{
    canvas = createCanvas(window.innerWidth/2.2, window.innerHeight);
    mobile_view = false;
	network_view = true
  }
  canvas.parent('sketch')
  colorMode(HSB);
  addPointstoArray();
  loadSentences();
  angleMode(DEGREES);
  frameRate(60)
  scroll_height = document.getElementById('text-body').scrollHeight;
}

function draw() {

  background(60, 3.7, 95.3, 1);
  wheel_scale = lerp(wheel_scale, init_scale + e, 0.05);
  drawPoints(wheel_scale, drag_x, drag_y);
  drawText()
  checkMouse();
  scroll_top = document.getElementById('text-body').scrollTop;
  percent = lerp(percent, map(scroll_top, 0, scroll_height - 1000, 0, 100), 0.1)
  changePercent();
  updateCompassAngle();
}

function changePercent() {
    document.getElementById('percent').innerText= str(round(percent)) + "%";
	document.getElementById('percent-mobile').innerText= str(round(percent)) + "%";
}

function checkMouse() {
  if(window.innerWidth > 950){
    if (mouseX > (window.innerWidth / 2.2) - text_view_padding) {
        check_mouse = false;
      } else {
        check_mouse = true;
      }
  }else{
    if ((mouseX > windowWidth) && network_view) {
        check_mouse = false;
      } else {
        check_mouse = true;
      }
  }
  
}


function mouseWheel(event) {
  if (check_mouse && network_view) {
    e += -event.delta * 0.005;
    if (e < -0.2) {
      e = -0.2
    }
	else if(e > 0.5) {
		e = 0.5
	}
  }else{
    e = 0
  }
}

function mouseDragged() { 

  let m_dragRX = -0.75
  let m_dragRY = -0.5
  if (check_mouse && network_view) {

    mouse_dragged = true;


	if(mobile_view){
		m_dragRX = -2;
		m_dragRY = -2;
	} else {
		m_dragRX = -0.75;
		m_dragRY = -0.5;
	}

    drag_x += ((mouseX - pmouseX) * m_dragRX)
    if (drag_x > 9000 || drag_x < -9000) {
      drag_x = 0;
    }
    drag_y += ((mouseY - pmouseY)  * m_dragRY)
    if (drag_y > 5000 || drag_y < -5000) {
      drag_y = 0;
    }
  }

  mouse_dragged = false;

}

function mouseClicked(event) {
  let x = 0;
  let y = 0;

  if (check_mouse && !mouse_dragged) {
    // Check for hover
    try {
      geoArray.forEach(element => {
        if (element.over == true) {
        
		  if ((e < 0.5) && !mobile_view)
		  {
			e += 0.25;
		  }	

          x = element.center_w - element.new_x
          y = element.center_h - element.new_y

          // Move to that area
          
          drag_x += (x - element.center_w) + 50
          drag_y += (y - windowHeight / 2) - 100
          smoothScroll(element.sequence);
          findNextNodeSeq(element);
          // Find next node in sequence
          throw new Error("Break the loop.")
        }
      });
    } catch (error) {
      
    }
  }
}

function findNextNodeSeq(geo) {
    let sequence = geo.sequence;
    let next = sequence + 1;
    geoArray.forEach(e => {
        if(e.sequence == next){
            next_text_seq = e;
        }
    })
}

function updateCompassAngle() {
    if(next_text_seq == null) {

    }else{
        let v1 = createVector(drag_x, drag_y);
        let v2 = createVector(next_text_seq.new_x, next_text_seq.new_y);
        direction = lerp(direction, v1.angleBetween(v2), 0.1);   
        let doc = document.getElementById('arrow-p');
        doc.style.transform = 'rotate('+ direction + 'deg)';
		doc = document.getElementById('arrow-mobile');
		doc.style.transform = 'rotate('+ direction + 'deg)';
    }
}

function addPointstoArray() { 
  for (let i = 0; i < 105; i++) {
    tmp = new Geo(data[i]);
    geoArray.push(tmp);
  }
}

function loadSentences() {
  geoArray.forEach(element => {
    element.spawnText();
  });
 }

function drawPoints(ws, dx, dy) {  
  
  for (let i = 0; i < geoArray.length; i++) {
    geoArray[i].update(ws, dx, dy);

  }

  push();
  noFill();
  stroke(255, 0, 0, 0.15);
  beginShape();
  for (let i = 0; i < geoArray.length; i++) {
    curveVertex(geoArray[i].center_w - geoArray[i].new_x * geoArray[i].ws, geoArray[i].center_h - geoArray[i].new_y * geoArray[i].ws);
  }
  endShape()
  pop();

  for (let i = 0; i < geoArray.length; i++) {
    geoArray[i].update(ws, dx, dy);
    geoArray[i].show(ws, dx, dy);
    geoArray[i].move()
    //geoArray[i].display();
    
  }

}

function drawText() {
	for (let i = 0; i < geoArray.length; i++) {
		geoArray[i].display();
	  }
}

// Resize Canvas Function
function windowResized() {
  if(window.innerWidth < 950){
    resizeCanvas(windowWidth, windowHeight);
    mobile_view = true;
  }else{
    resizeCanvas(windowWidth/2.2, windowHeight);
    mobile_view = false;
	network_view = true
  }
}

function smoothScroll(seq_id) {
  let id = '#' + seq_id
  document.getElementById(seq_id).scrollIntoView({
    behavior: 'smooth',
    inline: 'center',
	block: 'center'
  });
}



class Geo { 

  constructor(entry) {
    this.emb_dict = createStringDict({});
    this.entry = entry;
    this.speaker = entry['speaker'];
    this.text = entry['text'];
    this.sequence = entry['sequence'];

    this.emb_dict.set('Technology', str(this.entry['Technology']));
    this.emb_dict.set('Art', str(this.entry['Art']));
    this.emb_dict.set('Ireland', str(this.entry['Ireland']));
    this.emb_dict.set('Organisation', str(this.entry['Organisation']));
    this.emb_dict.set('Digital', str(this.entry['Digital']));
    this.emb_dict.set('Community', str(this.entry['Community']));
    this.emb_dict.set('Events', str(this.entry['Events']));

    this.radius = 100;
    this.new_radius = this.radius;

    this.over = false;
    this.ws = 1

    this.x = entry['x'] * 400;
    this.y = entry['y'] * 400;

    this.new_x = this.x;
    this.new_y = this.y;

    this.center_w = windowWidth / 4;
    this.center_h = windowHeight / 2;

    this.angle_counter_x = random(0, 100)
    this.angle_counter_y = random(0, 100)
    this.angle_counter_color = random(0, 100)
    this.angle_counter = random(-0.02, 0.02);
    this.angle_counter_pos = random(-0.2, 0.2);
    this.random_divider_x = random(2, 4);
    this.random_divider_y = random(2, 4);

    this.px = 0;
    this.py = 0;

    this.ang = 0;
  }


  spawnText() { 
    var dom_target = document.getElementById('text-body');

    // Create Div & Set Attributes
    var temp_div = document.createElement("div");
    temp_div.setAttribute('class', 'sentence-block');
    temp_div.setAttribute('id', str(this.sequence));

    // Create P for Speaker, X&Y, and Text
    var para_speaker = document.createElement('span');
    var node = document.createTextNode(this.speaker);
    para_speaker.setAttribute('class', this.speaker);
    para_speaker.appendChild(node);

    var para_x = document.createElement('span');
    node = document.createTextNode(round(this.center_w - this.new_x * this.ws));
    let id_x = str(this.sequence) + 'x';
    para_x.setAttribute('id', id_x);
    para_x.setAttribute('class', 'x-coord');
    para_x.appendChild(node);

    var para_y = document.createElement('span');
    node = document.createTextNode(round(this.center_h - this.new_y * this.ws));
    let id_y = str(this.sequence) + 'y';
    para_y.setAttribute('id', id_y);
    para_y.setAttribute('class', 'y-coord');
    para_y.appendChild(node);

    var node_link = document.createElement('span');
	node_link = document.createElement('img')
	node_link.src = "static/assets/data/assets/arrow-r.svg"
    // node = document.createTextNode('🡥')
    let node_pos = str(this.sequence) + 'pos';
    node_link.setAttribute('id', node_pos);
    node_link.setAttribute('class', 'arrow');
    node_link.appendChild(node);
    node_link.addEventListener("click", () => {
        let x = 0;
        let y = 0;

        
        try {
        geoArray.forEach(element => {
            if (element.sequence == this.sequence) {
            
            

            x = element.center_w - element.new_x
            y = element.center_h - element.new_y

            // Move to that area
            
            drag_x += (x - element.center_w) + 50;
          	drag_y += (y - windowHeight / 2) - 100;
            
            throw new Error("Break the loop.")
            }
        });
        } catch (error) {
        
        }
    });

    var para_text = document.createElement('p');
    node = document.createTextNode(this.text);
    para_text.appendChild(node);

    temp_div.appendChild(para_speaker);
    temp_div.appendChild(para_x);
    temp_div.appendChild(para_y);
    temp_div.appendChild(node_link);
    temp_div.appendChild(para_text);

    dom_target.appendChild(temp_div);
  }

  update(ws, dx, dy) { 

    if(window.innerWidth > 950){
        this.center_w = windowWidth / 4;
    }else{
        this.center_w = windowWidth / 2;
    }
    this.ws = ws;
    this.new_radius = this.radius * this.ws
    let rd_x = this.random_divider_x * this.ws
    let rd_y = this.random_divider_y * this.ws
    
    let p = this.new_radius / rd_x * sin(this.angle_counter_x)
    let q = this.new_radius / rd_y * cos(this.angle_counter_y)

    // this.center_w = windowWidth / 4;
    // this.center_h = windowHeight / 2;
  
    this.new_x = lerp(this.new_x, this.x + dx + p, 0.1);
    this.new_y = lerp(this.new_y, this.y + dy + q, 0.1);
    
    this.px = lerp(this.x, this.x + p, 0.05);
    this.py = lerp(this.y, this.y + q, 0.05);

    this.angle_counter_x += this.angle_counter_pos;
    this.angle_counter_y += this.angle_counter_pos;

    // Update Coords in Dom
    let id_string_x = str(this.sequence) + 'x';
    let id_string_y = str(this.sequence) + 'y';
    let x_text = str(round(this.px));
    let y_text = str(round(this.py));
    let arrow_text = str(this.sequence) + 'pos';
    document.getElementById(id_string_x).innerText = x_text;
    document.getElementById(id_string_y).innerText = y_text;   
  }


  show() { 
    noStroke();
    smooth();

    let tech_color = map(float(this.emb_dict.get('Technology')), -0.1, 0.1, 0, 255);
    let art_color = map(float(this.emb_dict.get('Art')), -0.1, 0.1, 0, 255);
    let ireland_color = map(float(this.emb_dict.get('Ireland')), -0.1, 0.1, 0, 255);

    let comm_color = map(float(this.emb_dict.get('Community')), -0.1, 0.1, 0, 255);
    let events_color = map(float(this.emb_dict.get('Events')), -0.1, 0.1, 0, 255);
    let org_color = map(float(this.emb_dict.get('Organisation')), -0.1, 0.1, 0, 255);

	let conicColors = [
		color(tech_color, art_color, 255, 255), 
		color(comm_color, events_color, 255, 255),
		color(ireland_color, org_color, 255, 255)
	]


	conicGradient(this.angle_counter_color, this.center_w - this.new_x * this.ws, this.center_h - this.new_y * this.ws, conicColors);
    ellipse(this.center_w - this.new_x * this.ws, this.center_h - this.new_y * this.ws, this.new_radius);

    this.angle_counter_color += this.angle_counter;
  }

  move() { 
    if (mouseX > (this.center_w - this.new_x * this.ws) - (this.new_radius/2) && mouseX < (this.center_w - this.new_x * this.ws) + (this.new_radius/2) && mouseY > (windowHeight / 2 - this.new_y * this.ws) - (this.new_radius/2) && mouseY < (windowHeight / 2 - this.new_y * this.ws) + (this.new_radius/2)) {
        this.over = true;
      }else {
        this.over = false;
      }
  }

  display() { 
    if (this.over && network_view) {
      let s = ""
      let t = ""
      t = round(this.emb_dict.get('Technology'), 2) + " : " + round(this.emb_dict.get('Art'), 2) + " : " + round(this.emb_dict.get('Community'), 2) + " : " + round(this.emb_dict.get('Events'), 2) + " : " + round(this.emb_dict.get('Ireland'), 2) + " : " + round(this.emb_dict.get('Digital'), 2) + " : " + round(this.emb_dict.get('Organisation'), 2);
      //s = round(this.px) + " : " + round(this.py);
      t = this.text
      s = this.speaker
      fill(0);
      textFont(myFont)
      push();
      fill(100, 0.6);
      noStroke();

	  let rectW = this.ws * 600
	  let rectH = this.ws * 400
	  


      rect((this.center_w - (this.new_x * this.ws)) - 300 * this.ws, (this.center_h - (this.new_y * this.ws)) - 500 * this.ws, rectW, rectH, 10);
      fill(0, 0, 0)
      textAlign(CENTER);
      textSize(map(this.ws, 0.5, 3, 15, 25 ));
      textWrap(WORD);
      text(t, (this.center_w - (this.new_x * this.ws)) - 200 * this.ws, (this.center_h - (this.new_y * this.ws)) - 400 * this.ws, 400 * this.ws, 200 * this.ws);
      fill(248, 63, 72)
      text(s, (this.center_w - (this.new_x * this.ws)) - 200 * this.ws, (this.center_h - (this.new_y * this.ws)) - (400 * this.ws) + 250 * this.ws, 400 * this.ws, 200 * this.ws);
      pop();
    }
  }

  


}

//Create listeners for both buttons
network_button.addEventListener('click', function handleClick() {
   if(mobile_view){
    network_view = true;

    var view_el = document.getElementById('text-view')
	view_el.style.opacity = 0

    view_el = document.getElementById('text-view-button')
    view_el.style.display = "inline";
	view_el.style.zIndex = "400"
   }
})

text_button.addEventListener('click', function handleClick() {
   network_view = false;

   var view_el = document.getElementById('text-view')
   view_el.style.opacity = 1
   view_el.style.display = "inline";

   setTimeout(() => {
	
	view_el = document.getElementById('text-view-button')
	view_el.style.zIndex = "0"
	view_el.style.display = "inline";
   }, 800)

//    view_el = document.getElementById('text-view-button')
//    view_el.style.zIndex = "0"
//    view_el.style.display = "inline";
})

document.getElementById('about-interview').addEventListener('click', function handleClick() {
	about_view = true
	document.getElementById('about-section').style.transform = "translate(-50%, -45%)"
})


function showAboutOnPageLoad(){
	about_view = true
	document.getElementById('about-section').style.transform = "translate(-50%, -45%)"
}

document.getElementById('mobile-btn').addEventListener('click', function handleClick() {

	if (about_view) {
		about_view = false
		document.getElementById('about-section').style.transform = "translate(-50%, 100%)"
	} else {
		about_view = true	
		document.getElementById('about-section').style.transform = "translate(-50%, -45%)"
	}
})

addEventListener("click", (evt) => {
	var my_div = document.getElementById('about-section')
	if(evt.target != my_div && evt.target != document.getElementById('about-interview') && evt.target.parentNode != my_div && evt.target != document.getElementById('mobile-about-button')  && evt.target != document.getElementById('mobile-btn')){
		
		if (about_view) {
			about_view = false
			document.getElementById('about-section').style.transform = "translate(-50%, 100%)"
		}
	}
});
