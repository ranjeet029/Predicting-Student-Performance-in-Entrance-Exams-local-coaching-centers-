const ctx=document.getElementById('subjectChart')

new Chart(ctx,{
type:'bar',

data:{

labels:['Maths','Physics','Chemistry','Biology'],

datasets:[{

label:'Average Marks',

data:[70,65,60,75]

}]

}

})