select reading_key from {{ ref('ai4i_clean') }}
where air_temperature_k <= 0 or process_temperature_k <= 0
   or rotational_speed_rpm <= 0 or torque_nm < 0 or tool_wear_min < 0
   or air_temperature_k is null or process_temperature_k is null
   or rotational_speed_rpm is null or torque_nm is null or tool_wear_min is null

