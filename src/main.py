import math
import matplotlib.pyplot as plt
import numpy as np
import keyboard
import random
import rospy
import tf
from tf2_msgs.msg import TFMessage
from initialization import initialize_state_covariance
from motion import update_pose
from nav_msgs.msg import Odometry
# Constants for the interface dimensions
WIDTH = 30
HEIGHT = 15

previous_time=0
start_time=0
position_x=position_y=0

# Variables for particle position, heading, and speed
particle_x = WIDTH // 2
particle_y = HEIGHT // 2
particle_heading = 0  # In degrees, 0 degrees is facing right
particle_speed = 10
angular_speed = 10


# Variables to store distances
distances = []

# Generate random number of landmarks and their positions
num_landmarks = random.randint(3, 6)

Fx = np.zeros((3, 2*num_landmarks + 3))
for i in range(3):
    Fx[i,i] = 1

#Initialize the state vetor and the convariance matrix
state_vector, covariance_matrix = initialize_state_covariance(num_landmarks)

print("State Vector:")
print(state_vector)

print("Covariance Matrix:")
print(covariance_matrix)

LANDMARKS = []
for _ in range(num_landmarks):
    landmark_x = random.randint(0, WIDTH)
    landmark_y = random.randint(0, HEIGHT)
    LANDMARKS.append((landmark_x, landmark_y))


# Create the figure and axis for the graph
fig, ax = plt.subplots()

# Function to calculate the Euclidean distance between two points
def calculate_distance(x1, y1, x2, y2):
    return math.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)

# Function to update the distance between the particle and landmarks
def update_distances():
    distances.clear()
    for landmark in LANDMARKS:
        distance = calculate_distance(particle_x, particle_y, landmark[0], landmark[1])
        distances.append(distance)

# Function to update the particle's position based on its heading and speed
def update_position():
    global particle_x, particle_y, particle_heading  # Declare as global to modify the global variables
    angle = math.radians(particle_heading)
    delta_x = particle_speed * math.cos(angle)
    delta_y = particle_speed * math.sin(angle)
    particle_x += int(delta_x)
    particle_y += int(delta_y)
    
def callback(msg):
    global previous_time
    global state_vector
    global start_time
    global position_x, position_y

    
    #rospy.loginfo("Received message: %s", msg.pose.pose)

    #rospy.loginfo("current time: %s.%s", msg.header.stamp.secs, msg.header.stamp.nsecs)

    orientation_x = msg.pose.pose.orientation.x
    orientation_y = msg.pose.pose.orientation.y
    orientation_z = msg.pose.pose.orientation.z
    orientation_w = msg.pose.pose.orientation.w
    
    position_x = msg.pose.pose.position.x
    position_y = msg.pose.pose.position.y

    velocity = msg.twist.twist.linear.x
    angular_velocity = msg.twist.twist.angular.z

     # Access the seconds and nanoseconds components of the timestamp
    timestamp_secs = msg.header.stamp.secs
    timestamp_nsecs = msg.header.stamp.nsecs

    time = float(str(timestamp_secs) + '.' + str(timestamp_nsecs).zfill(9))
    if previous_time == 0:
        previous_time=time
        dt=0
    else:
        dt=time-previous_time
        
        previous_time=time
        
    if start_time == 0:
        start_time=time

    elapsed_time=time-start_time
    
    # Convert the orientation data to Euler angles     
    quarternion = (orientation_x, orientation_y, orientation_z, orientation_w)
    euler = tf.transformations.euler_from_quaternion(quarternion)
        
    # Extract roll, pitch, and yaw from Euler angles
    roll = euler[0]
    pitch = euler[1]
    yaw = euler[2]
        
     # Set the flag to indicate new data arrival
    new_data_flag = True

    """ print("tempo: \n", dt, "angulo: \n", yaw)
    print("Velocity: ",velocity, "Angular Velocity: ",angular_velocity,"\n") """
    #Running the motion model
    state_vector = update_pose(state_vector,Fx, dt, velocity, num_landmarks, angular_velocity)

    #print("state_vector: \n", state_vector)

    return new_data_flag

def callback_fiducial(msg):
    rospy.loginfo("Received message: %s", msg.transform)
    

# Initialize the ROS node
rospy.init_node('subscriber_node')
new_data_flag = False
# Create a Subscriber object
sub = rospy.Subscriber('/pose', Odometry, callback)

sub2 = rospy.Subscriber('/fiducial_transforms', TFMessage, callback_fiducial)

# Main loop
while True:
    # Update distances
    update_distances()
    
    if new_data_flag:
        # New data is available, perform necessary operations
        # Reset the flag
        print("testing")
        new_data_flag = False

 
    # Print distances
    #print("Distances to landmarks:")
    #for i, distance in enumerate(distances):
        #print(f"Landmark {i+1}: {distance:.2f}") 


    # Clear the previous plot
    #ax.clear()

    # Plot the particle position
    #ax.plot(particle_x, particle_y, 'ro', label='Particle')

    # Plot the landmark positions
    #for i, landmark in enumerate(LANDMARKS):
        #ax.plot(landmark[0], landmark[1], 'bo', label=f'Landmark {i+1}')
        
    #print("State Vector:", state_vector)
        
    ax.plot(state_vector[0], state_vector[1], 'go', markersize=1)

    ax.plot(position_x, position_y, 'bo', markersize=1)
    
    # Set the axis limits
    ax.set_xlim(-WIDTH, WIDTH)
    ax.set_ylim(-HEIGHT, HEIGHT*2)

    # Set the title and labels
    ax.set_title('Active Particle')
    ax.set_xlabel('X')
    ax.set_ylabel('Y')

    # Update the legend
    ax.legend()

    # Display the plot
    plt.pause(0.01)

    # Read keyboard input
    """ if keyboard.is_pressed('up'):
        update_position()
    elif keyboard.is_pressed('left'):
        particle_heading += angular_speed
    elif keyboard.is_pressed('right'):
        particle_heading -= angular_speed
    elif keyboard.is_pressed('x'):
            particle_speed += 1
    elif keyboard.is_pressed('z'):
            particle_speed -= 1
            print("particle speed:", particle_speed)
    elif keyboard.is_pressed('s'):
            angular_speed += 1
    elif keyboard.is_pressed('a'):
            angular_speed -= 1
    elif keyboard.is_pressed('q'):
        break  # Exit the program if 'q' key is pressed """

    # Limit particle position within the interface dimensions
    particle_x = max(0, min(WIDTH - 1, particle_x))
    particle_y = max(0, min(HEIGHT - 1, particle_y))

# Close the plot window
plt.close(fig)